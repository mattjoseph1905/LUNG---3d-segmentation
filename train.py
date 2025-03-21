from os.path import join

import hydra
import lightning as L
import torch
from lightning.pytorch.callbacks import (
    EarlyStopping,
    LearningRateMonitor,
    ModelCheckpoint,
)
from pytorch_lightning.loggers import TensorBoardLogger
from omegaconf import DictConfig
from src.data_module import DecathlonDataModule
from src.model import DecathlonModel
from src.utils import generate_run_id


@hydra.main(version_base=None, config_path="conf", config_name="config")
def train(cfg: DictConfig) -> None:
    # generate unique run id based on current date & time
    run_id = generate_run_id()

    # Seed everything for reproducibility
    L.seed_everything(cfg.seed, workers=True)
    torch.set_float32_matmul_precision("high")

    # Initialize DataModule
    dm = DecathlonDataModule(
        root_dir=cfg.root_dir,
        task=cfg.task,
        batch_size=cfg.batch_size,
        num_workers=cfg.num_workers,
        seed=cfg.seed
    )
    dm.setup()

    # Init model from datamodule's attributes
    model = DecathlonModel(
        # num_classes=dm.num_classes,
        learning_rate=cfg.learning_rate,
        use_scheduler=cfg.use_scheduler,
    )

    # Init logger
    logger = TensorBoardLogger(save_dir=cfg.logs_dir, name="", version=run_id)
    # Init callbacks
    checkpoint_callback = ModelCheckpoint(
        monitor="val_loss",
        mode="min",
        save_top_k=2,
        dirpath=join(cfg.checkpoint_dirpath, run_id),
        filename="{epoch}-{step}-{val_loss:.2f}-{val_dice:.2f}",
    )

    # Init LearningRateMonitor
    lr_monitor = LearningRateMonitor(logging_interval="step")

    # early stopping
    early_stopping = EarlyStopping(
        monitor="val_loss",
        patience=10,
        verbose=True,
        mode="min",
    )

    # Initialize Trainer
    trainer = L.Trainer(
        max_epochs=cfg.max_epochs,
        accelerator="auto",
        devices="auto",
        logger=logger,
        callbacks=[checkpoint_callback, lr_monitor, early_stopping],
    )

    # Train the model
    trainer.fit(model, dm)


if __name__ == "__main__":
    train()