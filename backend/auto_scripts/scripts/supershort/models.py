# models.py
def get_lightgbm_params():
    """
    定义三种不同的LightGBM模型参数
    """
    params_list = [
        {
            'boosting_type': 'gbdt',
            'objective': 'regression',
            'metric': 'rmse',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'name': 'GBDT'
        },
        {
            'boosting_type': 'dart',
            'objective': 'regression',
            'metric': 'rmse',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'drop_rate': 0.1,
            'name': 'DART'
        },
        {
            'boosting_type': 'goss',
            'objective': 'regression',
            'metric': 'rmse',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'top_rate': 0.2,
            'other_rate': 0.1,
            'name': 'GOSS'
        }
    ]
    return params_list
