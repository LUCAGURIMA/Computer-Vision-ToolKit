# Segmentação - YOLOv8

## Usar

1. **Copie seu dataset aqui:**
   ```
   dataset/
   ├── images/
   │   ├── train/
   │   ├── val/
   │   └── test/
   ├── labels/
   │   ├── train/
   │   ├── val/
   │   └── test/
   └── data.yaml  ← OBRIGATÓRIO
   ```

2. **Arquivo data.yaml deve conter:**
   ```yaml
   path: C:\...\dataset
   train: images/train
   val: images/val
   test: images/test
   nc: 3
   names: ['impureza', 'mancha', 'oleo']
   ```

3. **Abra o notebook:**
   ```bash
   jupyter notebook segmentation_training.ipynb
   ```

4. **Execute as células em ordem** (Setup → Treinar → Testar)

5. **Modelo treinado em:**
   ```
   runs/fruta_seg/weights/best.pt
   ```

## Parâmetros Principais (célula 2)

- `MODEL`: yolov8n-seg (ou s-seg, m-seg, l-seg, x-seg)
- `EPOCHS`: 50
- `BATCH_SIZE`: 16 (reduzir se ficar sem memória)
- `DEVICE`: 0 (GPU) ou -1 (CPU)
- `SAVE_NAME`: nome do modelo
