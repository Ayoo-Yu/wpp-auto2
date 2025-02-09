from sqlalchemy import text
import threading

def test_connection_pool_stress(test_db):
    """测试连接池在高并发下的表现"""
    results = []
    errors = []
    
    def query_db(conn):
        try:
            result = conn.execute(text("SELECT 1")).scalar()
            results.append(result)
        except Exception as e:
            errors.append(str(e))
        finally:
            conn.close()  # 确保关闭连接
    
    threads = []
    for _ in range(20):  # 模拟20并发
        conn = test_db.connect()
        t = threading.Thread(target=query_db, args=(conn,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()  # 等待所有线程完成
    
    assert len(errors) == 0, f"发现连接错误: {errors}"
    assert len(results) == 20, "连接未正确回收" 