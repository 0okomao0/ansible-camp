import os
import shutil
import subprocess
import time

import ansible_runner
import requests
import yaml

API_BASE_URL = "http://localhost:8000"
POLL_INTERVAL = 5

def send_event_to_api(event_data: dict):
    try:
        requests.post(
            f"{API_BASE_URL}/api/v1/jobs/events", json=event_data, timeout=5
        )
    except Exception as e:
        print(f"Failed to send event to API: {e}")

def get_jobs():
    try:
        res = requests.get(
            f"{API_BASE_URL}/api/v1/jobs/ne?job_count=1", timeout=5
        )
    except Exception as e:
        print(f"Failed to get jobs from API: {e}")
        return []
    return res.json()
    
def on_ansible_event(event: dict):
    event_type = event.get("event")
    if event_type in [
        "runner_on_ok",
        "runner_on_failed",
        "runner_on_unreachable",
        "runner_on_skipped",
    ]:
        event_info = event.get("event_data", {})
        res = event_info.get("res", {})

        status = "OK"
        if event_type == "runner_on_failed":
            status = "FAILED"
        elif event_type == "runner_on_unreachable":
            status = "UNREACHABLE"
        elif event_type == "runner_on_skipped":
            status = "SKIPPED"

        payload = {
            "job_id": job_id,
            "event_type": event_type,
            "host": event_info.get("host"),
            "task": event_info.get("task"),
            "status": status,
            "changed": res.get("changed", False),
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "msg": res.get("msg", ""),
        }

        send_event_to_api(payload)

def runner_exec(job_id):
    res = requests.get(f"{API_BASE_URL}/api/v1/inventory")
    inventory_yaml = yaml.dump(res.json())

    try:
        send_event_to_api(
            {"job_id": job_id, "event_type": "job_started", "status": "RUNNING"}
        )

        print(f'{os.path.join(os.getenv("HOST_WORKSPACE"), "test/runner_files")}')
        r = ansible_runner.run(
            private_data_dir=os.path.join(os.getenv("HOST_WORKSPACE"), "test/runner_files"),
            playbook="ping.yml",
            inventory=inventory_yaml,
            # verbosity=3,
            process_isolation=True,
            process_isolation_executable="docker",
            container_image="test-ee:v1.0",
            event_handler=on_ansible_event,
        )

        send_event_to_api(
            {
                "job_id": job_id,
                "event_type": "job_finished",
                "status": r.status,
            }
        )

    finally:
        if os.path.isdir("test/inventory"):
            shutil.rmtree("test/inventory")

def builder_exec(job_id):
    command = [
        "ansible-builder", "build",
        "--tag", "test-ee:v1.0",
        "--file", "test/builder_files/execution-environment.yml"
    ]
    send_event_to_api(
        {"job_id": job_id, "event_type": "job_prepare_started", "status": "PREPARING"}
    )
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    print(f"{result=}")
    if result.returncode == 0:
        send_event_to_api(
            {"job_id": job_id, "event_type": "job_prepare_finished", "status": "PREPARED", "stdout": result.stdout, "stderr": result.stderr}
        )
    else:
        send_event_to_api(
            {"job_id": job_id, "event_type": "job_prepare_finished", "status": "FAILED", "stdout": result.stdout, "stderr": result.stderr}
        )
    return result.returncode

def process_job(job_id):
    print(f"[{job_id}] process_job stated.")
    builder_rc = builder_exec(job_id)
    if builder_rc != 0:
        print(f"[{job_id}] ansible-builder exited non-zero code: {builder_rc}")
        return

    runner_exec(job_id)

def worker_loop():
    print("Worker started.")
    while True:
        print(f"Polling for jobs... INTERVAL: {POLL_INTERVAL}s")
        jobs = []
        jobs = get_jobs()
        if len(jobs) > 0:
            for job in jobs:
                global job_id
                job_id = job["id"]
                process_job(job_id)
        else:
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    worker_loop()