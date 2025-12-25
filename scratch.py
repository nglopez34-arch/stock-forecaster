import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class KalmanFilterParams:
    """Parameters for the kinematic Kalman filter on log returns."""
    q_level: float = 1e-3  # Process noise for level state
    q_trend: float = 1e-4  # Process noise for trend/momentum state
    r_obs: float = 1e-5  # Observation noise variance
    rho: float = 0.8  # Mean reversion parameter for trend (0 < rho < 1)


# Preset configurations for different use cases
PRESETS = {
    # For ML feature extraction - responsive, preserves signal structure
    'responsive': KalmanFilterParams(
        q_level=1e-3,
        q_trend=1e-4,
        r_obs=1e-5,
        rho=0.8
    ),
    # Moderate smoothing - balances noise reduction with signal preservation
    'balanced': KalmanFilterParams(
        q_level=5e-4,
        q_trend=5e-5,
        r_obs=5e-5,
        rho=0.85
    ),
    # Heavy smoothing - extracts slow-moving trends only
    'smooth': KalmanFilterParams(
        q_level=1e-5,
        q_trend=1e-6,
        r_obs=1e-4,
        rho=0.95
    ),
}


class KinematicKalmanFilter:
    """
    Kalman filter for decomposing log returns into level + trend components.

    State vector: [level, trend]
    - level: filtered "true" log return
    - trend: momentum/acceleration term (rate of change of returns)

    This is analogous to tracking position and velocity, but applied to
    the return space (so we're tracking "velocity" and "acceleration"
    in the original price space).
    """

    def __init__(self, params: Optional[KalmanFilterParams] = None, preset: str = 'responsive'):
        if params is not None:
            self.params = params
        else:
            self.params = PRESETS.get(preset, PRESETS['responsive'])
        self._build_system_matrices()

    def _build_system_matrices(self):
        """Construct the state-space matrices."""
        p = self.params

        # State transition matrix
        # x_{t+1} = F @ x_t + w_t
        # level_{t+1} = level_t + trend_t
        # trend_{t+1} = rho * trend_t  (mean-reverting)
        self.F = np.array([
            [1.0, 1.0],
            [0.0, p.rho]
        ])

        # Process noise covariance
        self.Q = np.array([
            [p.q_level, 0.0],
            [0.0, p.q_trend]
        ])

        # Observation matrix (we observe the level component)
        self.H = np.array([[1.0, 0.0]])

        # Observation noise variance
        self.R = np.array([[p.r_obs]])

    def filter(self, log_returns: np.ndarray) -> dict:
        """
        Run the Kalman filter on a series of log returns.

        Returns a dictionary with all the decomposed signals useful for ML.
        """
        n = len(log_returns)

        # Storage for outputs
        x_filtered = np.zeros((n, 2))  # Filtered state estimates
        x_predicted = np.zeros((n, 2))  # One-step-ahead predictions
        P_filtered = np.zeros((n, 2, 2))  # Filtered covariances
        P_predicted = np.zeros((n, 2, 2))  # Predicted covariances
        innovations = np.zeros(n)  # Prediction errors
        innovation_var = np.zeros(n)  # Innovation variances
        kalman_gains = np.zeros((n, 2))  # Kalman gain vectors
        log_likelihoods = np.zeros(n)  # For model diagnostics

        # Initialize state and covariance
        # Use first few observations to get reasonable starting values
        init_window = min(20, n // 4)
        x = np.array([
            np.mean(log_returns[:init_window]),  # Initial level
            0.0  # Initial trend (assume zero)
        ])
        P = np.eye(2) * 1e-3  # Initial uncertainty

        for t in range(n):
            # === PREDICT STEP ===
            x_pred = self.F @ x
            P_pred = self.F @ P @ self.F.T + self.Q

            x_predicted[t] = x_pred
            P_predicted[t] = P_pred

            # === UPDATE STEP ===
            y = log_returns[t]

            # Innovation (prediction error)
            y_pred = self.H @ x_pred
            innovation = y - y_pred[0]
            innovations[t] = innovation

            # Innovation covariance
            S = self.H @ P_pred @ self.H.T + self.R
            innovation_var[t] = S[0, 0]

            # Kalman gain
            K = P_pred @ self.H.T @ np.linalg.inv(S)
            kalman_gains[t] = K.flatten()

            # Update state and covariance
            x = x_pred + K.flatten() * innovation
            P = (np.eye(2) - K @ self.H) @ P_pred

            x_filtered[t] = x
            P_filtered[t] = P

            # Log-likelihood for this observation (Gaussian)
            log_likelihoods[t] = -0.5 * (np.log(2 * np.pi * S[0, 0]) +
                                         innovation ** 2 / S[0, 0])

        return {
            'filtered_level': x_filtered[:, 0],  # Denoised return
            'filtered_trend': x_filtered[:, 1],  # Momentum/trend state
            'predicted_level': x_predicted[:, 0],  # One-step prediction
            'predicted_trend': x_predicted[:, 1],
            'innovations': innovations,  # Surprise component
            'innovation_std': np.sqrt(innovation_var),
            'normalized_innovations': innovations / np.sqrt(innovation_var),  # Should be ~N(0,1)
            'kalman_gain_level': kalman_gains[:, 0],
            'kalman_gain_trend': kalman_gains[:, 1],
            'uncertainty_level': np.sqrt(P_filtered[:, 0, 0]),
            'uncertainty_trend': np.sqrt(P_filtered[:, 1, 1]),
            'log_likelihood': np.sum(log_likelihoods),
        }


def create_kalman_features(prices: pd.Series, preset: str = 'responsive') -> pd.DataFrame:
    """
    Create a feature DataFrame from price series using Kalman decomposition.

    Parameters
    ----------
    prices : pd.Series
        Price series (e.g., adjusted close)
    preset : str
        Parameter preset: 'responsive', 'balanced', or 'smooth'

    Returns
    -------
    pd.DataFrame
        Features suitable for LSTM input
    """
    # Compute log returns
    log_returns = np.log(prices / prices.shift(1)).dropna().values

    # Initialize the filter with chosen preset
    kf = KinematicKalmanFilter(preset=preset)

    # Run filter on full series
    result = kf.filter(log_returns)

    # Build feature DataFrame
    features = pd.DataFrame(index=prices.index[1:])  # Align with returns

    # Raw return for reference
    features['log_return'] = log_returns

    # Kalman-derived features
    features['kf_level'] = result['filtered_level']  # Denoised return
    features['kf_trend'] = result['filtered_trend']  # Momentum state
    features['kf_innovation'] = result['innovations']  # Surprise
    features['kf_norm_innovation'] = result['normalized_innovations']  # Standardized surprise
    features['kf_predicted'] = result['predicted_level']  # Model's prediction
    features['kf_gain'] = result['kalman_gain_level']  # Observation weight
    features['kf_uncertainty'] = result['uncertainty_level']  # State uncertainty

    # Derived features that might be useful
    features['kf_signal_noise_ratio'] = (
            np.abs(result['filtered_level']) / (result['uncertainty_level'] + 1e-10)
    )
    features['kf_trend_strength'] = (
            np.abs(result['filtered_trend']) / (result['uncertainty_trend'] + 1e-10)
    )

    return features


def create_multiscale_kalman_features(prices: pd.Series) -> pd.DataFrame:
    """
    Create features using multiple Kalman filters at different timescales.

    This captures both fast-moving and slow-moving dynamics simultaneously.
    """
    log_returns = np.log(prices / prices.shift(1)).dropna().values

    features = pd.DataFrame(index=prices.index[1:])
    features['log_return'] = log_returns

    for name, preset in PRESETS.items():
        kf = KinematicKalmanFilter(params=preset)
        result = kf.filter(log_returns)

        features[f'kf_{name}_level'] = result['filtered_level']
        features[f'kf_{name}_trend'] = result['filtered_trend']
        features[f'kf_{name}_innovation'] = result['innovations']
        features[f'kf_{name}_norm_innov'] = result['normalized_innovations']
        features[f'kf_{name}_gain'] = result['kalman_gain_level']

    # Cross-scale features: differences between fast and slow filters
    features['kf_fast_slow_diff'] = (
            features['kf_responsive_level'] - features['kf_smooth_level']
    )
    features['kf_trend_divergence'] = (
            features['kf_responsive_trend'] - features['kf_smooth_trend']
    )

    return features


# === Example Usage ===
if __name__ == "__main__":
    import yfinance as yf
    import matplotlib.pyplot as plt

    # Fetch some data
    ticker = "AAPL"
    data = yf.download(ticker, start="2020-01-01", end="2024-01-01", progress=False)

    # Handle the MultiIndex columns that yfinance now returns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    prices = data['Close']

    # Create Kalman features with responsive preset
    features = create_kalman_features(prices, preset='responsive')

    print("\nFeature DataFrame:")
    print(features.tail(10))
    print(f"\nFeature columns: {list(features.columns)}")

    # Visualize the decomposition
    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)

    # Recent window for clarity
    plot_data = features.iloc[-252:]

    ax = axes[0]
    ax.plot(plot_data.index, plot_data['log_return'], alpha=0.5, label='Raw Log Return')
    ax.plot(plot_data.index, plot_data['kf_level'], linewidth=1.5, label='Kalman Filtered')
    ax.set_ylabel('Log Return')
    ax.legend()
    ax.set_title(f'{ticker} - Kalman Decomposition of Log Returns')

    ax = axes[1]
    ax.plot(plot_data.index, plot_data['kf_trend'], color='green')
    ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('Trend/Momentum')
    ax.set_title('Estimated Momentum State (Return Acceleration)')

    ax = axes[2]
    ax.plot(plot_data.index, plot_data['kf_norm_innovation'], color='purple', alpha=0.7)
    ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
    ax.axhline(2, color='red', linestyle=':', alpha=0.5)
    ax.axhline(-2, color='red', linestyle=':', alpha=0.5)
    ax.set_ylabel('Normalized Innovation')
    ax.set_title('Innovation (Surprise) - Should be ~N(0,1) if model is correct')

    ax = axes[3]
    ax.plot(plot_data.index, plot_data['kf_gain'], color='orange')
    ax.set_ylabel('Kalman Gain')
    ax.set_title('Kalman Gain (Weight on New Observation vs Prediction)')
    ax.set_xlabel('Date')

    plt.tight_layout()
    plt.savefig('kalman_decomposition.png', dpi=150)
    plt.show()

    # Check innovation statistics
    print("\n=== Innovation Diagnostics ===")
    innov = features['kf_norm_innovation'].dropna()
    print(f"Mean: {innov.mean():.4f} (should be ~0)")
    print(f"Std:  {innov.std():.4f} (should be ~1)")
    print(f"Skew: {innov.skew():.4f}")
    print(f"Kurt: {innov.kurtosis():.4f} (excess, should be ~0 for Gaussian)")

    # Autocorrelation of innovations
    from statsmodels.stats.diagnostic import acorr_ljungbox

    lb_result = acorr_ljungbox(innov, lags=[10], return_df=True)
    print(f"\nLjung-Box test (lag 10): p-value = {lb_result['lb_pvalue'].values[0]:.4f}")
    print("(p < 0.05 suggests autocorrelation remains - potential for LSTM to exploit)")

    # === Demonstrate multiscale features ===
    print("\n\n=== Multiscale Kalman Features ===")
    multiscale_features = create_multiscale_kalman_features(prices)
    print(f"Multiscale feature columns: {list(multiscale_features.columns)}")

    # Plot comparison of scales
    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
    plot_data = multiscale_features.iloc[-252:]

    ax = axes[0]
    ax.plot(plot_data.index, plot_data['log_return'], alpha=0.3, label='Raw')
    ax.plot(plot_data.index, plot_data['kf_responsive_level'], label='Responsive', linewidth=1.5)
    ax.plot(plot_data.index, plot_data['kf_balanced_level'], label='Balanced', linewidth=1.5)
    ax.plot(plot_data.index, plot_data['kf_smooth_level'], label='Smooth', linewidth=1.5)
    ax.set_ylabel('Level')
    ax.legend()
    ax.set_title('Multi-scale Kalman Filtered Returns')

    ax = axes[1]
    ax.plot(plot_data.index, plot_data['kf_responsive_trend'], label='Responsive')
    ax.plot(plot_data.index, plot_data['kf_balanced_trend'], label='Balanced')
    ax.plot(plot_data.index, plot_data['kf_smooth_trend'], label='Smooth')
    ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('Trend')
    ax.legend()
    ax.set_title('Multi-scale Momentum States')

    ax = axes[2]
    ax.plot(plot_data.index, plot_data['kf_fast_slow_diff'], color='purple')
    ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('Fast - Slow')
    ax.set_title('Cross-scale Divergence (Responsive - Smooth)')
    ax.set_xlabel('Date')

    plt.tight_layout()
    plt.savefig('kalman_multiscale.png', dpi=150)
    plt.show()