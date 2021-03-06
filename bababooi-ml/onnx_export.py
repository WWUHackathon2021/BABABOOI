#!/usr/bin/env python3
import argparse

import torch

from models import DummyModel, QuickDraw


def get_args():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-c', '--checkpoint', help='Path to a model checkpoint.')
    parser.add_argument('-o', '--out', default='model.onnx', help='ONNX write path')
    parser.add_argument('-t', '--type', choices=['dummy', 'quickdraw', 'nlpfeud'], default='dummy',
                        help='Type of model to export.')
    return parser.parse_args()


def main(args):
    if args.type == 'dummy':
        model = DummyModel.load_from_checkpoint(args.checkpoint)
    elif args.type == 'quickdraw':
        model = QuickDraw.load_from_checkpoint(args.checkpoint)
    elif args.type == 'nlpfeud':
        raise ValueError(f'Use hf_convert_graph_to_onnx.py to convert nlpfeud model to onnx.')
    else:
        raise ValueError(f'Model type {args.type} not supported.')

    x = torch.rand(1, 1, 256, 256, requires_grad=True)
    model.to_onnx(args.out, x, export_params=True, input_names=['input'], output_names=['output'],
                  dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}})


if __name__ == '__main__':
    args = get_args()
    main(args)
