import numpy as np
import lightgbm as lgb
from lightgbm import LGBMRegressor
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import make_scorer, mean_squared_error

def find_best_params(X, y, K=5, n_iter=30, random_state=42):
    """优化 LightGBM 参数，并支持 GPU 加速"""
    
    # **1. 启用 GPU**
    gpu_params = {
        'device': 'gpu',  # 启用 GPU
        'gpu_platform_id': 0,  # 选择平台（如果有多个）
        'gpu_device_id': 0,  # 选择 GPU 设备
        'gpu_use_dp': False  # 关闭双精度，提高计算效率
    }
    
    # **2. 限制搜索范围，提高效率**
    param_dist = {
        'boosting_type': ['gbdt', 'goss'],
        'num_leaves': np.arange(20, 100, 10),  # 步长10，减少搜索空间
        'learning_rate': [0.01, 0.05, 0.1, 0.2],
        'feature_fraction': [0.6, 0.7, 0.8, 0.9],
        'max_depth': np.arange(3, 10),  # 限制最大深度
        'n_estimators': np.arange(50, 200, 20),  # 限制弱学习器数量
    }
    
    mse_scorer = make_scorer(mean_squared_error, greater_is_better=False)

    # **3. 创建 GPU 加速的 LGBMRegressor**
    lgbm = LGBMRegressor(random_state=random_state, **gpu_params)

    # **4. 采用并行计算（但限制 `n_jobs` 以减少内存开销）**
    random_search = RandomizedSearchCV(
        estimator=lgbm,
        param_distributions=param_dist,
        n_iter=n_iter,
        scoring=mse_scorer,
        cv=K,
        random_state=random_state,
        n_jobs=2,  # 限制线程数，防止 OOM
        verbose=1
    )

    # **5. 使用 LightGBM 的 early stopping**
    fit_params = {
        "early_stopping_rounds": 10,
        "eval_metric": "rmse",
        "eval_set": [(X, y)],
        "verbose": False
    }

    # **6. 处理大数据，防止 OOM**
    X = np.float32(X)  # 降低数据精度，减少内存占用
    y = np.float32(y)

    # **7. 运行优化**
    random_search.fit(X, y, **fit_params)

    # **8. 打印每一折的验证结果**
    print("\nCross-validation results per fold:")
    for fold_idx, score in enumerate(random_search.cv_results_['mean_test_score']):
        print(f"Fold {fold_idx+1}: MSE = {-score:.5f}")

    best_search_params = random_search.best_params_

    default_params = {
        'objective': 'regression',
        'metric': 'rmse'
    }

    if best_search_params.get('boosting_type', 'gbdt') == 'goss':
        default_params['name'] = 'GOSS'
    else:
        default_params['name'] = 'GBDT'

    best_param_dict = {**default_params, **best_search_params}

    return best_param_dict
