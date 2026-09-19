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

    # Never fabricate training data. An empty dataset is a setup error, not
    # something to paper over -- training on placeholder images produces a model
    # whose metrics mean nothing.
    for split_name, split_dir in (('train', train_dir), ('val', val_dir)):
        if not os.path.exists(split_dir) or sum(len(files) for _, _, files in os.walk(split_dir)) == 0:
            raise SystemExit(
                f"ERROR: {split_name} split is missing or empty:\n  {split_dir}\n\n"
                "Run dataset/scripts/01_curate_dataset.py first."
            )

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
        
    num_classes = len(image_datasets['train'].classes)
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)

    model = model.to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    # Two-phase transfer learning. Fine-tuning every layer at 1e-3 from the start
    # destroys the pretrained ImageNet features -- the backbone needs a much
    # smaller step than a randomly initialised head.
    #   phase 1: backbone frozen, train only the new classifier head
    #   phase 2: unfreeze everything, fine-tune at a low learning rate
    head_epochs = int(os.environ.get("STYLESYNC_HEAD_EPOCHS", 5))
    finetune_epochs = int(os.environ.get("STYLESYNC_EPOCHS", 25))
    num_epochs = head_epochs + finetune_epochs

    for p in model.features.parameters():
        p.requires_grad = False

    optimizer = optim.Adam(model.classifier.parameters(), lr=1e-3)
    scheduler = None

    checkpoint_path = os.path.join(checkpoint_dir, 'mobilenetv2_fashion.pth')

    best_val_acc = 0.0
    best_epoch = -1
    epochs_since_best = 0
    patience = int(os.environ.get("STYLESYNC_PATIENCE", 8))

    print(f"Phase 1: training classifier head for {head_epochs} epochs "
          f"({num_classes} classes, {len(image_datasets['train'])} train images)")

    for epoch in range(num_epochs):
        if epoch == head_epochs:
            # Phase 2 -- unfreeze the backbone and drop the learning rate.
            for p in model.features.parameters():
                p.requires_grad = True
            optimizer = optim.Adam(model.parameters(), lr=1e-4)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode='max', factor=0.5, patience=2
            )
            print(f"\nPhase 2: fine-tuning all layers at lr=1e-4 for {finetune_epochs} epochs")

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

            if phase == 'val':
                if scheduler is not None:
                    scheduler.step(float(epoch_acc))

                # Keep the best-validating weights, not whichever epoch is last.
                if float(epoch_acc) > best_val_acc:
                    best_val_acc = float(epoch_acc)
                    best_epoch = epoch
                    epochs_since_best = 0
                    torch.save(model.state_dict(), checkpoint_path)
                    print(f'  -> new best val acc {best_val_acc:.4f}, checkpoint saved')
                else:
                    epochs_since_best += 1

        if epochs_since_best >= patience:
            print(f"\nNo improvement for {patience} epochs; stopping early at epoch {epoch}.")
            break

    print("Training complete")

    if best_epoch < 0:
        raise SystemExit("ERROR: no epoch improved on validation accuracy; nothing was saved.")

    print(f"Best checkpoint: epoch {best_epoch}, val acc {best_val_acc:.4f} -> {checkpoint_path}")
    print("Now run model/evaluate.py to regenerate metrics and checkpoints/metadata.json.")

if __name__ == '__main__':
    train_model()
