# Ansible Camp

CMDB（構成管理データベース）とAnsible ジョブ管理を提供する、FastAPI ベースの API サーバー

- WIP
    - CMDB Update
    - Ansible Job Execution
    - Playbook EDITOR
    - GUI


## 要件

- Python 3.12 以上
- uv（Pythonパッケージマネージャー）
- MariaDB データベース（MySQLも可）

## 開発環境構築

1. リポジトリをクローン：
```bash
git clone https://github.com/0okomao0/ansible-camp.git
```
2. .devcontainer/.env_sampleを元に、.devcontainer/.envを作成

3. 該当ディレクトリをdevcontainerとして開く

4. サーバーが起動したら、下記コマンドを実行
```
uv run uvicorn app.main:app --reload
```
以下のURLでアクセス可能となる：

APIServer: http://localhost:8000/api/v1
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc


## 主な依存関係
    fastapi - Webフレームワーク
    uvicorn - ASGIサーバー
    ansible-core - Ansible コアライブラリ
    ansible-runner - Ansible実行エンジン
    sqlalchemy - ORM
    pydantic - データバリデーション

完全な依存関係は pyproject.toml を参照のこと
