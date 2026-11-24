"""Push the backend to a Hugging Face Docker Space.

    pip install huggingface_hub
    huggingface-cli login          # a token with write access
    python backend/scripts/deploy_hf_space.py <user>/<space-name> [--env-file backend/.env.production]

Creates the Space if it doesn't exist, uploads the files the Dockerfile needs,
and (with --env-file) stores each KEY=value as a Space secret. The Space then
builds and restarts on its own.
"""
import argparse
from pathlib import Path

from huggingface_hub import HfApi

BACKEND = Path(__file__).resolve().parents[1]

# Everything the image needs; the rest of backend/ stays local.
ALLOW = ["Dockerfile", ".dockerignore", "requirements.txt", "app/**"]
IGNORE = [
    "**/__pycache__/**",
    "**/*.pyc",
    "app/modules/ai/checkpoints/*.candidate.pth",
    "app/modules/ai/checkpoints/mobilenetv2_fashion.pth",
]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            values[key.strip()] = value
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("space_id", help="e.g. yourname/stylesync-api")
    parser.add_argument("--env-file", type=Path, help="KEY=value file to store as Space secrets")
    args = parser.parse_args()

    api = HfApi()
    api.create_repo(args.space_id, repo_type="space", space_sdk="docker", exist_ok=True)

    if args.env_file:
        for key, value in read_env(args.env_file).items():
            api.add_space_secret(args.space_id, key, value)
            print(f"secret set: {key}")

    api.upload_folder(
        repo_id=args.space_id,
        repo_type="space",
        folder_path=BACKEND,
        allow_patterns=ALLOW,
        ignore_patterns=IGNORE,
        commit_message="Deploy StyleSync backend",
    )
    api.upload_file(
        repo_id=args.space_id,
        repo_type="space",
        path_or_fileobj=BACKEND / "deploy" / "space_README.md",
        path_in_repo="README.md",
        commit_message="Space config",
    )

    owner, name = args.space_id.split("/", 1)
    host = f"{owner}-{name}".lower().replace("_", "-").replace(".", "-")
    print(f"\nPushed. Build logs: https://huggingface.co/spaces/{args.space_id}")
    print(f"API base URL once it's running: https://{host}.hf.space/api/v1")


if __name__ == "__main__":
    main()
