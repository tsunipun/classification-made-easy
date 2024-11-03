from models.modeling import VisionTransformer, CONFIGS
import torch
import logging
import numpy as np
import argparse
import random
import os
from PIL import Image
from torchvision import transforms, datasets
import vit_args

logger = logging.getLogger(__name__)

def setup(args):
    # Prepare model
    config = CONFIGS[args.model_type]
    class_folders = [f.name for f in os.scandir(args.dataset_path) if f.is_dir()]
    num_classes = len(class_folders)

    model = VisionTransformer(config, args.img_size, zero_head=True, num_classes=num_classes)
    logger.info(args.pretrained_dir)
    if args.pretrained_dir.endswith('npz'):
        model.load_from(np.load(args.pretrained_dir))
    elif args.pretrained_dir.endswith('bin'):
        model.load_state_dict(torch.load(args.pretrained_dir))
    model.to(args.device)
    num_params = count_parameters(model)

    logger.info("{}".format(config))
    logger.info("Training parameters %s", args)
    logger.info("Total Parameter: \t%2.1fM" % num_params)
    print(num_params)
    return args, model

def count_parameters(model):
    params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return params/1000000

def set_seed(args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.n_gpu > 0:
        torch.cuda.manual_seed_all(args.seed)

def main(input_image):
    args = vit_args.args
    
    checkpoints_path = os.path.join(os.path.dirname(__file__), 'output')
    previous_checkpoints = os.listdir(checkpoints_path)
    if(len(previous_checkpoints) > 0):
        previous_checkpoints.sort()
        args.pretrained_dir = os.path.join(checkpoints_path, previous_checkpoints[-1])

    # Setup CUDA, GPU & distributed training
    if args.local_rank == -1:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        args.n_gpu = torch.cuda.device_count()
    else:  # Initializes the distributed backend which will take care of sychronizing nodes/GPUs
        torch.cuda.set_device(args.local_rank)
        device = torch.device("cuda", args.local_rank)
        torch.distributed.init_process_group(backend='nccl', timeout=timedelta(minutes=60))
        args.n_gpu = 1
    args.device = device

    # Setup logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO if args.local_rank in [-1, 0] else logging.WARN)
    logger.warning("Process rank: %s, device: %s, n_gpu: %s, distributed training: %s, 16-bits training: %s" %
                   (args.local_rank, args.device, args.n_gpu, bool(args.local_rank != -1), args.fp16))

    # Set seed
    set_seed(args)

    # Model & Tokenizer Setup
    args, model = setup(args)

    # Training
    return test(args, model, input_image)
    
def prepare_input(image, args):
    # if not isinstance(input, Image.Image):
    #     image = Image.open(input).convert('RGB')
    
    mTransforms = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ])
    
    image = mTransforms(image)
    image = image.unsqueeze(0)
    image = image.to(args.device)
    return image
    
    
def test(args, model, input_image):
    model.eval()
    inp = prepare_input(input_image, args)
    logits = model(inp)[0]
    print(logits)
    preds = torch.argmax(logits, dim=-1)
    conf = torch.max(logits)
    if(conf < 2.0):
        return "Can't recognize"
    pred = preds.detach().cpu().numpy()[0]
    
    class_names = [f.name for f in os.scandir(args.dataset_path) if f.is_dir()]
    class_names.sort()
    logger.info(class_names[pred])
    return class_names[pred]
    
if __name__ == "__main__":
    if not os.path.exists('checkpoint/ViT-B_16.npz'):
        os.system('wget https://storage.googleapis.com/vit_models/imagenet21k/ViT-B_16.npz -P checkpoint')
    main()