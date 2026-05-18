"""
Generate engineered features from raw data. This is essentially preprocessing step 1.
Winsorize and interpolate at this step also.
"""
import pandas as pd
import numpy as np
import os
from multiprocessing import Pool, cpu_count
import time


def clean_dataframe(df):
    """Remove duplicates and sort the dataframe"""
    if df.empty:
        return df

    # Remove duplicate (symbol, timestamp) pairs, keeping the last occurrence
    df = df.drop_duplicates(subset=['symbol', 'timestamp'], keep='last')

    # Sort by symbol and timestamp for clean organization
    df = df.sort_values(['symbol', 'timestamp']).reset_index(drop=True)

    return df


def preprocess_chunk(symbols_chunk):
    """
    Process a chunk of symbols and generate features

    Args:
        symbols_chunk: tuple of (symbols_list, full_dataframe)

    Returns:
        DataFrame with engineered features for the symbols in this chunk
    """
    symbols, df = symbols_chunk

    # Filter to only the symbols in this chunk
    chunk_df = df[df['symbol'].isin(symbols)].copy()

    if chunk_df.empty:
        return chunk_df

    # Process each symbol
    result_dfs = []
    for symbol in symbols:
        symbol_df = chunk_df[chunk_df['symbol'] == symbol].copy()

        if symbol_df.empty:
            continue

        # Sort by timestamp
        symbol_df = symbol_df.sort_values('timestamp')

        # Interpolate missing values in price columns
        price_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in price_columns:
            if col in symbol_df.columns:
                symbol_df[col] = symbol_df[col].interpolate(method='linear', limit_direction='both')

        # Winsorize to handle outliers (clip at 1st and 99th percentile)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in symbol_df.columns:
                lower = symbol_df[col].quantile(0.01)
                upper = symbol_df[col].quantile(0.99)
                symbol_df[col] = symbol_df[col].clip(lower, upper)

        # Generate features
        # EWMA of close with multiple spans
        symbol_df['ewma_5'] = symbol_df['close'].ewm(span=5, adjust=False).mean()
        symbol_df['ewma_20'] = symbol_df['close'].ewm(span=20, adjust=False).mean()
        symbol_df['ewma_60'] = symbol_df['close'].ewm(span=60, adjust=False).mean()

        # Returns
        symbol_df['returns'] = symbol_df['close'].pct_change()

        # Log returns
        symbol_df['log_returns'] = np.log(symbol_df['close'] / symbol_df['close'].shift(1))

        # Volatility (rolling std of returns)
        symbol_df['volatility_20'] = symbol_df['returns'].rolling(window=20).std()

        # Price momentum
        symbol_df['momentum_5'] = symbol_df['close'] / symbol_df['close'].shift(5) - 1
        symbol_df['momentum_20'] = symbol_df['close'] / symbol_df['close'].shift(20) - 1

        # Volume features
        if 'volume' in symbol_df.columns:
            symbol_df['volume_ewma_20'] = symbol_df['volume'].ewm(span=20, adjust=False).mean()
            symbol_df['volume_ratio'] = symbol_df['volume'] / symbol_df['volume_ewma_20']

        result_dfs.append(symbol_df)

    # Combine all symbols in this chunk
    if result_dfs:
        return pd.concat(result_dfs, ignore_index=True)
    else:
        return pd.DataFrame()


def split_symbols_into_chunks(symbols, num_chunks):
    """Split symbols into roughly equal chunks"""
    symbols = list(symbols)
    chunk_size = len(symbols) // num_chunks
    if chunk_size == 0:
        chunk_size = 1

    chunks = []
    for i in range(0, len(symbols), chunk_size):
        chunks.append(symbols[i:i + chunk_size])

    return chunks


def parallel_preprocess(df):
    """
    Apply preprocessing in parallel by splitting symbols across cores

    Args:
        df: DataFrame with raw data

    Returns:
        DataFrame with engineered features
    """
    # Number of CPU cores available
    num_cores = cpu_count()

    # Get unique symbols
    unique_symbols = df['symbol'].unique()

    # Split symbols into chunks
    symbol_chunks = split_symbols_into_chunks(unique_symbols, num_cores)

    # Create tuples of (symbols_list, dataframe) for each chunk
    chunks_with_data = [(chunk, df) for chunk in symbol_chunks]

    # Create a pool of workers (one for each CPU core)
    with Pool(processes=num_cores) as pool:
        # Process the chunks in parallel
        processed_chunks = pool.map(preprocess_chunk, chunks_with_data)

    # Concatenate the processed chunks back into one DataFrame
    processed_df = pd.concat(processed_chunks, ignore_index=True)

    return processed_df


# Example usage
if __name__ == "__main__":
    start_time = time.time()
    raw_data = pd.read_parquet("../data/raw_data.parquet")

    # If there already exists an incomplete file
    if os.path.exists("../data/data_w_features.parquet"):
        featured_data = pd.read_parquet("../data/data_w_features.parquet")

        # Get symbols that haven't been processed yet
        processed_symbols = set(featured_data['symbol'].unique())
        all_symbols = set(raw_data['symbol'].unique())
        remaining_symbols = all_symbols - processed_symbols

        if remaining_symbols:
            # Process only the remaining symbols
            remaining_data = raw_data[raw_data['symbol'].isin(remaining_symbols)]
            new_featured_data = parallel_preprocess(remaining_data)
            featured_data = pd.concat([featured_data, new_featured_data], ignore_index=True)
        else:
            print("All symbols already processed")

    # If there does not yet exist any file
    else:
        featured_data = parallel_preprocess(raw_data)

    featured_data = clean_dataframe(featured_data)
    featured_data.to_parquet("data_w_features.parquet")
    end_time = time.time()
    print(f"It took {end_time - start_time} seconds to compute")