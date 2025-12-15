import logging
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image

logger = logging.getLogger(__name__)

# Singleton Global de IA para no recargar modelo en cada request
_model = None
_processor = None
_device = "cpu"

def load_ai_model():
    global _model, _processor, _device
    if _model is not None:
        return _model, _processor, _device

    try:
        logger.info("🧠 Loading CLIP Model into Backend Memory...")
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = "openai/clip-vit-base-patch32"
        
        _model = CLIPModel.from_pretrained(model_name).to(_device)
        _processor = CLIPProcessor.from_pretrained(model_name)
        logger.info(f"✅ CLIP Model Loaded on {_device}")
    except Exception as e:
        logger.error(f"❌ Error loading AI Model: {e}")
        return None, None, "cpu"
        
    return _model, _processor, _device

def get_image_embedding(image_file):
    """
    Genera embedding para una imagen (PIL Image o path o file-like object)
    """
    model, processor, device = load_ai_model()
    if not model:
        return None

    try:
        # Si es un archivo subido de Django (InMemoryUploadedFile), abrirlo con PIL
        if hasattr(image_file, 'read'):
            image = Image.open(image_file).convert("RGB")
        else:
            image = image_file

        inputs = processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
        
        # Normalizar
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        return image_features.cpu().numpy()[0].tolist()
    except Exception as e:
        logger.error(f"Error vectorizing image: {e}")
        return None
