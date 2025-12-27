"""
Generate parquet file that stores mean and std for some features for every symbol in raw_data.parquet.
This information will be used for training and inference to normalize certain features later on in normalize.py.
This is to be reran when and only when the model is trained.
"""
import pandas as pd
import numpy as np


def main():
    pass


if __name__ == "__main__":
    main()