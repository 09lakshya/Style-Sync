# Backend image for a Hugging Face Docker Space (also runs on any Docker host).
FROM python:3.12-slim

# libglib2.0-0 is what opencv-python-headless still links against.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as uid 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PORT=7860
WORKDIR /home/user/app

# CPU-only torch is a fraction of the size of the default CUDA build.
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --user -r requirements.txt

# Bake CLIP into the image so a restart doesn't re-download ~600 MB.
ARG CLIP_MODEL_NAME=openai/clip-vit-base-patch32
RUN python -c "from transformers import CLIPModel, CLIPProcessor; CLIPModel.from_pretrained('${CLIP_MODEL_NAME}'); CLIPProcessor.from_pretrained('${CLIP_MODEL_NAME}')"

# The classifier loads app/modules/ai/checkpoints relative to this directory.
COPY --chown=user app ./app

EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
