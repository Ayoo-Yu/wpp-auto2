<template>
  <div class="power-compare-container power-predict-container">
    <!-- 添加背景动画层 -->
    <div class="background-container">
      <div class="animated-background"></div>
    </div>

    <h1 class="page-title">预测结果对比分析</h1>

    <!-- 时间选择与配置区域 -->
    <div class="config-panel">
      <el-card class="time-picker-card">
        <div class="time-range-picker">
          <span class="label">选择时间范围：</span>
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
          <el-button 
            type="primary" 
            @click="fetchComparisonData"
            :loading="loading"
          >
            查询数据
          </el-button>
        </div>
      </el-card>

      <el-card class="type-select-card">
        <div class="type-checkbox-group">
          <span class="label">选择展示类型：</span>
          <el-checkbox-group v-model="selectedTypes">
            <el-checkbox label="实测值" />
            <el-checkbox label="超短期预测" />
            <el-checkbox label="短期预测" />
            <el-checkbox label="中期预测" />
          </el-checkbox-group>
        </div>
      </el-card>
    </div>

    <!-- 图表展示区域 -->
    <div class="chart-container">
      <div class="chart-wrapper">
        <div v-if="!chartData" class="empty-chart">
          <el-icon class="empty-icon"><PieChart /></el-icon>
          <p class="empty-text">请选择时间范围并查询数据</p>
        </div>
        <canvas v-show="chartData" ref="chartCanvas" style="height: 70vh !important;"></canvas>
      </div>
    </div>

    <!-- 加载状态 -->
    <LoadingIndicator 
      :visible="loading" 
      message="数据加载中..."
    />
  </div>
</template>

<script>
import { Chart, CategoryScale, LinearScale, LineElement, PointElement, Title, Tooltip, Legend, LineController } from 'chart.js'
import axios from 'axios'

Chart.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  LineController
)

export default {
  name: 'PowerCompare',
  data() {
    return {
      backendBaseUrl: 'http://127.0.0.1:5000',
      timeRange: [],
      selectedTypes: ['实测值', '超短期预测'],
      chartData: null,
      chartInstance: null,
      loading: false,
      wfcapacity: 453.5
    }
  },
  methods: {
    async fetchComparisonData() {
      if (!this.timeRange || this.timeRange.length !== 2) {
        this.$message.error('请选择完整的时间范围')
        return
      }

      this.loading = true
      try {
        const response = await axios.post(`${this.backendBaseUrl}/power-compare/data`, {
          start: this.timeRange[0],
          end: this.timeRange[1],
          types: this.selectedTypes
        })

        this.processChartData(response.data)
      } catch (error) {
        this.$message.error('数据获取失败')
        console.error(error)
      } finally {
        this.loading = false
      }
    },

    processChartData(data) {
      this.chartData = data
      const datasets = []
      const colors = {
        '实测值': '#FF6B6B',
        '超短期预测': '#4ECDC4',
        '短期预测': '#45B7D1',
        '中期预测': '#96CEB4'
      }

      // 收集所有时间戳
      const timestamps = new Set()
      Object.values(data).forEach(values => {
        values.forEach(v => timestamps.add(v.timestamp))
      })

      const sortedTimestamps = Array.from(timestamps)
        .map(ts => new Date(ts).getTime())
        .sort((a, b) => a - b)
        .map(ts => new Date(ts).toISOString())

      const labels = sortedTimestamps.map(ts => {
        const date = new Date(ts)
        return `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2,'0')}`
      })

      // 首先添加实测值数据集
      if (data['实测值']) {
        const actualMap = new Map(data['实测值'].map(v => [
          new Date(v.timestamp).toISOString(),
          v.power
        ]))
        
        datasets.push({
          label: '实测值',
          data: sortedTimestamps.map(ts => actualMap.get(ts) || null),
          borderColor: colors['实测值'],
          backgroundColor: `${colors['实测值']}33`,
          tension: 0.3,
          pointRadius: 3,
          spanGaps: true
        })
      }

      // 处理预测值数据集
      ['超短期预测', '短期预测', '中期预测'].forEach(type => {
        if (data[type] && data['实测值']) {
          const predictedMap = new Map(data[type].map(v => [
            new Date(v.timestamp).toISOString(),
            v.power
          ]))

          // 计算评估指标
          const predictedValues = []
          const actualValues = []
          
          data[type].forEach(pred => {
            const predTime = new Date(pred.timestamp).getTime()
            const actualPoint = data['实测值'].find(
              act => new Date(act.timestamp).getTime() === predTime
            )
            if (actualPoint) {
              predictedValues.push(pred.power)
              actualValues.push(actualPoint.power)
            }
          })

          if (predictedValues.length > 0) {
            const metrics = this.calculateMetrics(actualValues, predictedValues)
            const metricsText = `${type} (MAE: ${metrics.mae.toFixed(1)} | RMSE: ${metrics.rmse.toFixed(1)} | ACC: ${(metrics.acc * 100).toFixed(1)}% | K: ${metrics.k.toFixed(2)} | Pe: ${metrics.pe.toFixed(1)})`
            
            datasets.push({
              label: metricsText,
              data: sortedTimestamps.map(ts => predictedMap.get(ts) || null),
              borderColor: colors[type],
              backgroundColor: `${colors[type]}33`,
              tension: 0.3,
              pointRadius: 3,
              spanGaps: true
            })
          }
        }
      })

      // 更新图表
      if (this.chartInstance) {
        this.chartInstance.destroy()
        this.chartInstance = null
      }

      this.$nextTick(() => {
        if (!this.$refs.chartCanvas) {
          console.error('Canvas element not found')
          setTimeout(() => {
            if (this.$refs.chartCanvas) {
              this.initChart()
            }
          }, 100)
          return
        }
        
        const ctx = this.$refs.chartCanvas.getContext('2d')
        this.chartInstance = new Chart(ctx, {
          type: 'line',
          data: {
            labels,
            datasets
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'top',
                labels: {
                  padding: 20,
                  font: {
                    size: 13
                  },
                  usePointStyle: true,
                  pointStyle: 'line'
                }
              },
              title: {
                display: true,
                text: '风电功率预测对比分析',
                font: {
                  size: 18
                },
                padding: 20
              }
            },
            scales: {
              x: {
                grid: { color: 'rgba(255,255,255,0.1)' },
                ticks: { 
                  color: '#666',
                  maxRotation: 45,
                  minRotation: 45
                }
              },
              y: {
                beginAtZero: true,
                suggestedMax: 500,
                title: {
                  display: true,
                  text: '功率 (MW)',
                  color: '#666'
                },
                grid: { color: 'rgba(255,255,255,0.1)' },
                ticks: { color: '#666' }
              }
            }
          }
        })
      })
    },

    calculateMetrics(actual, predicted) {
      const threshold = 0.2 * this.wfcapacity
      
      // 计算 MAE
      const mae = predicted.reduce((sum, p, i) => sum + Math.abs(p - actual[i]), 0) / predicted.length
      
      // 计算 MSE 和 RMSE
      const mse = predicted.reduce((sum, p, i) => sum + Math.pow(p - actual[i], 2), 0) / predicted.length
      const rmse = Math.sqrt(mse)
      
      // 计算 ACC
      const acc = 1 - rmse / this.wfcapacity
      
      // 计算 Pe
      const pe = acc < 0.83 ? (0.83 - acc) * this.wfcapacity : 0
      
      // 计算 K
      const m_values = predicted.map((p, i) => {
        const actualVal = Math.max(actual[i], threshold)
        return Math.pow((p - actual[i]) / actualVal, 2)
      })
      const k = 1 - Math.sqrt(m_values.reduce((sum, v) => sum + v, 0) / m_values.length)
      
      return { mae, mse, rmse, acc, k, pe }
    },

    initChart() {
      const ctx = this.$refs.chartCanvas.getContext('2d')
      if (this.chartInstance) {
        this.chartInstance.destroy()
      }
      this.chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: []
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top' },
            title: { 
              display: true,
              text: '风电功率预测对比分析' 
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.1)' },
              ticks: { color: '#666' }
            },
            y: {
              beginAtZero: true,
              suggestedMax: 500,
              title: { 
                display: true, 
                text: '功率 (MW)',
                color: '#666'
              },
              grid: { color: 'rgba(255,255,255,0.1)' },
              ticks: { color: '#666' }
            }
          }
        }
      })
    }
  },
  beforeUnmount() {
    if (this.chartInstance) {
      this.chartInstance.destroy()
    }
  }
}
</script>

<style scoped>
.power-compare-container {
  min-height: 100vh;
  position: relative;
  padding: 40px;
  color: #fff;
  overflow: hidden;  /* 确保背景动画不会溢出 */
}

/* 添加背景容器样式 */
.background-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  overflow: hidden;
}

/* 添加动画背景样式 */
.animated-background {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(
    135deg,
    #43cea2 0%,
    #185a9d 50%,
    #43cea2 100%
  );
  animation: gradient 15s ease infinite;
  transform-origin: center center;
  z-index: -1;
}

/* 添加背景动画关键帧 */
@keyframes gradient {
  0% {
    transform: rotate(0deg);
  }
  50% {
    transform: rotate(180deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.page-title {
  color: #ffffff;
  font-size: 32px;
  font-weight: 600;
  margin-bottom: 40px;
  text-align: center;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.config-panel {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.time-picker-card, .type-select-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.time-range-picker {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
}

.type-checkbox-group {
  padding: 20px;
}

.label {
  color: #333;
  font-weight: 500;
}

.chart-container {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  padding: 24px;
  height: 75vh;
  margin-top: 20px;
}

.chart-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.empty-chart {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #909399;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

canvas {
  width: 100% !important;
  height: 100% !important;
}

:deep(.chartjs-size-monitor) {
  width: 100% !important;
  height: 100% !important;
}

@media (max-width: 768px) {
  .config-panel {
    grid-template-columns: 1fr;
  }

  .time-range-picker {
    flex-direction: column;
    align-items: stretch;
  }
}
</style> 