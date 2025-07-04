"""
 Copyright (c) 2022, salesforce.com, inc.
 All rights reserved.
 SPDX-License-Identifier: BSD-3-Clause
 For full license text, see the LICENSE_Lavis file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import argparse
import os
import random

import numpy as np
import torch
import torch.backends.cudnn as cudnn
import wandb

import minigpt4.tasks as tasks
from minigpt4.common.config import Config
from minigpt4.common.dist_utils import get_rank, init_distributed_mode
from minigpt4.common.logger import setup_logger
from minigpt4.common.registry import registry
from minigpt4.common.utils import now

# imports modules for registration
from minigpt4.datasets.builders import *
from minigpt4.models import *
from minigpt4.processors import *
from minigpt4.runners import *
from minigpt4.tasks import *


def parse_args():
    parser = argparse.ArgumentParser(description="Training")
    parser.add_argument("--cfg-path", required=True, help="path to configuration file.")
    parser.add_argument(
        "--options",
        nargs="+",
        help="override some settings in the used config, the key-value pair "
        "in xxx=yyy format will be merged into config file (deprecate), "
        "change to --cfg-options instead.",
    )
    args = parser.parse_args()
    return args


def setup_seeds(config):
    seed = config.run_cfg.seed + get_rank()
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    cudnn.benchmark = False
    cudnn.deterministic = True


def main():
    # Register library root path
    registry.register_path("library_root", os.path.dirname(os.path.abspath(__file__)))
    
    # Parse arguments
    args = parse_args()
    
    print(f"Library root: {registry.get_path('library_root')}")
    print(f"Loading config from: {args.cfg_path}")
    
    # Load and initialize configuration
    cfg = Config(args)
    
    # Initialize distributed training
    init_distributed_mode(cfg.run_cfg)
    setup_seeds(cfg)
    setup_logger()
    
    cfg.pretty_print()

    task = tasks.setup_task(cfg)
    datasets = task.build_datasets(cfg)
    model = task.build_model(cfg)
    
    if cfg.run_cfg.wandb_log:
        wandb.login()
        wandb.init(project="minigptv", name=cfg.run_cfg.job_name)
        wandb.watch(model)

    runner = get_runner_class(cfg)(
        cfg=cfg, job_id=now(), task=task, model=model, datasets=datasets
    )
    runner.train()


def get_runner_class(cfg):
    """
    Get runner class from config. Default to epoch-based runner.
    """
    runner_cls = registry.get_runner_class(cfg.run_cfg.get("runner", "runner_base"))
    return runner_cls


if __name__ == "__main__":
    main()
