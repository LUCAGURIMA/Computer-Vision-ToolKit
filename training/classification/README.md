# Classificação - YOLOv8

## Usar

1. **Copie seu dataset aqui:**
   ```
   dataset/
   ├── train/
   │   ├── BOA/
   │   │   ├── img1.jpg
   │   │   └── img2.jpg
   │   └── RUIM/
   │       ├── img1.jpg
   │       └── img2.jpg
   ├── val/
   │   ├── BOA/
   │   └── RUIM/
   ```

2. **Abra o notebook:**
   ```bash
   jupyter notebook classification_training.ipynb
   ```

3. **Execute as células em ordem** (Setup → Treinar → Testar)

4. **Modelo treinado em:**
   ```
   runs/fruta_clf/weights/best.pt
   ```

## Parâmetros Principais (célula 2)

- `MODEL`: yolov8n-cls (ou s-cls, m-cls, l-cls, x-cls)
- `EPOCHS`: 50 (mais para datasets pequenos, menos para grandes)
- `BATCH_SIZE`: 16 (reduzir se ficar sem memória)
- `DEVICE`: 0 (GPU) ou -1 (CPU)
- `SAVE_NAME`: nome do modelo
