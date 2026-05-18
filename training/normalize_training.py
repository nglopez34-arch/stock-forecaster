"""
Generate metadata.parquet that stores mean and std for some features for every symbol in raw_data.parquet.
Uses metadata.parquet to normalize some features in data_w_features.parquet.
Output is processed_training_data.parquet, almost ready for training the neural networks.
"""