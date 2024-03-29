import math
import torch
from config import (
    TRAINING_EPOCH, NUM_CLASSES, IN_CHANNELS, BCE_WEIGHTS, BACKGROUND_AS_CLASS, TRAIN_CUDA
)
from torch.nn import CrossEntropyLoss
#from dataset import get_train_val_test_Dataloaders
from dataset_fets import get_train_val_test_Dataloaders
from torch.optim import Adam
from torch.utils.tensorboard import SummaryWriter
from unet3d import UNet3D
from transforms import (train_transform, train_transform_cuda,
                        val_transform, val_transform_cuda)

if BACKGROUND_AS_CLASS: NUM_CLASSES += 1

writer = SummaryWriter("runs")

model = UNet3D(in_channels=IN_CHANNELS , num_classes= NUM_CLASSES)
train_transforms = train_transform
val_transforms = val_transform

"""if torch.cuda.is_available() and TRAIN_CUDA:
    model = model.to('cuda')
    train_transforms = train_transform_cuda
    val_transforms = val_transform_cuda 
elif not torch.cuda.is_available() and TRAIN_CUDA:
    print('cuda not available! Training initialized on cpu ...')
"""
model = model.to('cuda')
train_dataloader, val_dataloader, _ = get_train_val_test_Dataloaders(train_transforms= train_transforms, val_transforms=val_transforms, test_transforms= val_transforms)


#criterion = CrossEntropyLoss(weight=torch.Tensor(BCE_WEIGHTS))
criterion = CrossEntropyLoss()
optimizer = Adam(params=model.parameters())

min_valid_loss = math.inf

for epoch in range(TRAINING_EPOCH):
    
    train_loss = 0.0
    model.train()
    c = 0
    for data in train_dataloader:
        print('Batch {}'.format(c))
        image, ground_truth = data['image'], data['label']
        image = image.to('cuda')
        ground_truth = ground_truth.to('cuda')
        optimizer.zero_grad()
        output = model(image)
        ground_truth = ground_truth.type(torch.LongTensor)
        loss = criterion(output.to('cpu'), ground_truth.to('cpu'))
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        c = c+1
    print('Epoch {}, train loss: {}'.format(epoch, train_loss))
    
    valid_loss = 0.0
    model.eval()
    for data in val_dataloader:
        image, ground_truth = data['image'], data['label']
        image = image.to('cuda')
        ground_truth = ground_truth.to('cuda')
        output = model(image)
        ground_truth = ground_truth.type(torch.LongTensor)
        loss = criterion(output.to('cpu'),ground_truth.to('cpu'))
        valid_loss = loss.item()
        
    writer.add_scalar("Loss/Train", train_loss / len(train_dataloader), epoch)
    writer.add_scalar("Loss/Validation", valid_loss / len(val_dataloader), epoch)
    
    print(f'Epoch {epoch+1} \t\t Training Loss: {train_loss / len(train_dataloader)} \t\t Validation Loss: {valid_loss / len(val_dataloader)}')
    
    if min_valid_loss > valid_loss:
        print(f'Validation Loss Decreased({min_valid_loss:.6f}--->{valid_loss:.6f}) \t Saving The Model')
        min_valid_loss = valid_loss
        # Saving State Dict
        torch.save(model.state_dict(), f'checkpoints/epoch{epoch}_valLoss{min_valid_loss}.pth')

writer.flush()
writer.close()

