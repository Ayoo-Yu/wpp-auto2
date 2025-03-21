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

def get_unified_params():
    """
    返回统一的模型超参数，将用于不同的数据子集训练
    """
    base_params = {
        'objective': 'regression',
        'metric': 'rmse',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
    }
    
    # 三种不同的算法参数
    gbdt_params = base_params.copy()
    gbdt_params.update({
        'boosting_type': 'gbdt',
        'name': 'GBDT'
    })
    
    dart_params = base_params.copy()
    dart_params.update({
        'boosting_type': 'dart',
        'drop_rate': 0.1,
        'name': 'DART'
    })
    
    goss_params = base_params.copy()
    goss_params.update({
        'boosting_type': 'goss',
        'top_rate': 0.2,
        'other_rate': 0.1,
        'name': 'GOSS'
    })
    
    return [gbdt_params, dart_params, goss_params]