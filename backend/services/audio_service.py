import uuid
import shutil

def save_uploaded_audio(file):
    filename = f"data/samples/{uuid.uuid4()}.wav"
    with open(filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return filename
