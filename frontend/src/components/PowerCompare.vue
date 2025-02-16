<template>
  <div class="power-compare-container model-train-container">
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
      loading: false
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

      Object.entries(data).forEach(([type, values]) => {
        const dataMap = new Map(values.map(v => [
          new Date(v.timestamp).toISOString(),
          v.power
        ]))
        const dataset = {
          label: type,
          data: sortedTimestamps.map(ts => dataMap.get(ts) || null),
          borderColor: colors[type],
          backgroundColor: `${colors[type]}33`,
          tension: 0.3,
          pointRadius: 3,
          spanGaps: true
        }
        datasets.push(dataset)
      })

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
            labels: labels,
            datasets
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

        console.log('Chart Data:', {
          labels: labels.slice(0, 5),  // 显示前5个标签
          datasets: datasets.map(d => ({
            label: d.label,
            data: d.data.slice(0, 5) // 显示前5个数据点
          }))
        })
      })
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
  padding: 40px;
  min-height: 100vh;
}

.config-panel {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.time-picker-card, .type-select-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.time-range-picker {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
}

.type-checkbox-group {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.label {
  font-weight: 500;
  color: #1d1d1f;
}

.chart-container {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16px;
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