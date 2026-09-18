import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models
from preprocess import get_transforms

def train_model():
    data_dir = r"C:\Users\Lakshya\Desktop\StyleSync\dataset\curated"
    checkpoint_dir = r"C:\Users\Lakshya\Desktop\StyleSync\backend\app\modules\ai\checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    train_dir = os.path.join(data_dir, 'train')
    val_dir = os.path.join(data_dir, 'val')
    
    # If the directories don't exist or are empty (because curation had no images), mock a tiny dataset for training script to run without crashing
    if not os.path.exists(train_dir) or sum(len(files) for _, _, files in os.walk(train_dir)) == 0:
        print("Warning: Train dataset not found. Generating dummy data for training.")
        from PIL import Image
        for split in ['train', 'val', 'test']:
            for cat in ['Casual', 'Party', 'Formal', 'Ethnic', 'Western', 'Summer', 'Winter']:
                cdir = os.path.join(data_dir, split, cat)
                os.makedirs(cdir, exist_ok=True)
                # create 2 dummy images
                for i in range(2):
                    Image.new('RGB', (224, 224), color = (73, 109, 137)).save(os.path.join(cdir, f"dummy_{i}.png"))
    
    image_datasets = {
        'train': datasets.ImageFolder(train_dir, get_transforms(is_training=True)),
        'val': datasets.ImageFolder(val_dir, get_transforms(is_training=False))
    }
    
    dataloaders = {
        'train': torch.utils.data.DataLoader(image_datasets['train'], batch_size=16, shuffle=True, num_workers=0),
        'val': torch.utils.data.DataLoader(image_datasets['val'], batch_size=16, shuffle=False, num_workers=0)
    }
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    # Load MobileNetV2
    # Setting weights=models.MobileNet_V2_Weights.DEFAULT works in newer torchvision
    # We can also use pretrained=True for backwards compat
    try:
        model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    except:
        model = models.mobilenet_v2(pretrained=True)
        
    num_ftrs = model.classifier[1].in_features
    # 7 classes
    model.classifier[1] = nn.Linear(num_ftrs, 7)
    
    model = model.to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    num_epochs = 2 # Small number for demonstration
    for epoch in range(num_epochs):
        print(f'Epoch {epoch}/{num_epochs - 1}')
        print('-' * 10)
        
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()
                
            running_loss = 0.0
            running_corrects = 0
            
            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)
                
                optimizer.zero_grad()
                
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)
                    
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()
                        
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                
            epoch_loss = running_loss / len(image_datasets[phase])
            epoch_acc = running_corrects.double() / len(image_datasets[phase])
            
            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')
            
    print("Training complete")
    
    # Save checkpoint
    checkpoint_path = os.path.join(checkpoint_dir, 'mobilenetv2_fashion.pth')
    torch.save(model.state_dict(), checkpoint_path)
    print(f"Model saved to {checkpoint_path}")

if __name__ == '__main__':
    train_model()
