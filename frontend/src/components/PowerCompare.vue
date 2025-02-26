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
          <div class="time-picker-wrapper">
            <span class="label">选择时间范围：</span>
            <el-date-picker
              v-model="timeRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </div>
          <div class="button-group">
            <el-button 
              type="primary" 
              @click="fetchComparisonData"
              :loading="loading"
            >
              查询数据
            </el-button>
            <el-button-group class="download-buttons">
              <el-button 
                type="success" 
                @click="downloadCSV"
                :disabled="!exportData.comparison"
              >
                CSV下载
              </el-button>
              <el-button 
                type="success" 
                @click="downloadMetricsCSV"
                :disabled="!exportData.metrics"
              >
                指标下载
              </el-button>
              <el-button 
                type="success" 
                @click="downloadSVG"
                :disabled="!chartData"
              >
                功率图下载
              </el-button>
              <el-button 
                type="success" 
                @click="downloadMetricSVG"
                :disabled="!dailyMetrics"
              >
                指标图下载
              </el-button>
            </el-button-group>
          </div>
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

    <!-- 每日指标区域 -->
    <div class="daily-metrics-container">
      <el-card class="metrics-card">
        <div class="metrics-header">
          <h3>每日评估指标</h3>
          <div class="metric-buttons">
            <el-radio-group v-model="currentMetric" @change="updateMetricChart">
              <el-radio-button label="acc">ACC (%)</el-radio-button>
              <el-radio-button label="mae">MAE (MW)</el-radio-button>
              <el-radio-button label="mse">MSE (MW²)</el-radio-button>
              <el-radio-button label="rmse">RMSE (MW)</el-radio-button>
              <el-radio-button label="k">K值</el-radio-button>
              <el-radio-button label="pe">Pe (MW)</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div class="metrics-chart-wrapper">
          <p v-if="!dailyMetrics" class="empty-text" style="text-align: center;display: flex;flex-direction: column;justify-content: center;align-items: center;color: #909399;">请选择时间范围并查询数据</p>
          <canvas 
            v-show="dailyMetrics" 
            ref="metricChart" 
            style="width: 100%; height: 100%; display: block;"
          ></canvas>
        </div>
      </el-card>
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
      selectedTypes: ['实测值', '短期预测'],
      chartData: null,
      chartInstance: null,
      loading: false,
      wfcapacity: 453.5,
      currentMetric: 'acc',
      dailyMetrics: null,
      metricChart: null,
      colors: {
        '超短期预测': '#4ECDC4',
        '短期预测': '#45B7D1',
        '中期预测': '#96CEB4'
      },
      exportData: {
        comparison: null,
        metrics: null
      },
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
      console.log('原始数据:', data)
      this.chartData = data

      // 计算每日指标
      console.log('开始计算每日指标')
      this.dailyMetrics = this.calculateDailyMetrics(data)
      console.log('每日指标结果:', this.dailyMetrics)

      // 创建主图表
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

      // 添加实测值数据集
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
      const predictionTypes = ['超短期预测', '短期预测', '中期预测'].filter(type => data[type])
      
      predictionTypes.forEach(type => {
        if (data['实测值']) {
          const predictedMap = new Map(data[type].map(v => [
            new Date(v.timestamp).toISOString(),
            v.power
          ]))

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

      // 更新指标图表
      this.$nextTick(() => {
        this.updateMetricChart()
      })

      // 存储导出数据
      this.exportData.comparison = {
        labels: labels,
        rawTimestamps: sortedTimestamps,
        datasets: datasets.reduce((acc, dataset) => {
          acc[dataset.label.split(' ')[0]] = dataset.data
          return acc
        }, {})
      }

      this.exportData.metrics = this.dailyMetrics
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
    },

    // 计算每日指标的方法
    calculateDailyMetrics(data) {
      console.log('计算每日指标的输入数据:', data)
      if (!data['实测值']) {
        console.warn('没有实测值数据')
        return null
      }

      const dailyMetrics = {}
      const predictionTypes = this.selectedTypes.filter(type => 
        type !== '实测值' && data[type]
      )
      console.log('预测类型:', predictionTypes)

      predictionTypes.forEach(type => {
        console.log(`处理预测类型: ${type}`)
        const metricsByDay = {}
        
        // 按日期分组数据
        data[type].forEach(pred => {
          const dateObj = new Date(pred.timestamp)
          const date = `${dateObj.getFullYear()}-${(dateObj.getMonth()+1).toString().padStart(2,'0')}-${dateObj.getDate().toString().padStart(2,'0')}`
          
          if (!metricsByDay[date]) {
            metricsByDay[date] = {
              predicted: [],
              actual: []
            }
          }

          const actualPoint = data['实测值'].find(
            act => new Date(act.timestamp).getTime() === new Date(pred.timestamp).getTime()
          )
          if (actualPoint) {
            metricsByDay[date].predicted.push(pred.power)
            metricsByDay[date].actual.push(actualPoint.power)
          }
        })

        console.log(`${type} 的每日数据:`, metricsByDay)

        // 计算每日指标
        dailyMetrics[type] = Object.entries(metricsByDay)
          .filter(([dateStr]) => {
            const date = new Date(dateStr)
            const startDate = new Date(this.timeRange[0])
            const endDate = new Date(this.timeRange[1])
            return date >= startDate && date <= endDate
          })
          .filter(([, dayData]) => dayData.predicted.length > 0)
          .map(([date, dayData]) => {
            const metrics = this.calculateMetrics(dayData.actual, dayData.predicted)
            return { date, ...metrics }
          })
          .sort((a, b) => new Date(a.date) - new Date(b.date))

        console.log(`${type} 的每日指标:`, dailyMetrics[type])
      })

      return dailyMetrics
    },

    // 更新指标图表的方法
    updateMetricChart() {
      console.log('开始更新指标图表')
      
      // 销毁旧图表
      if (this.metricChart) {
        console.log('销毁旧图表')
        this.metricChart.destroy()
        this.metricChart = null
      }

      // 等待 DOM 更新
      this.$nextTick(() => {
        const canvas = this.$refs.metricChart
        if (!canvas) {
          console.error('Canvas element not found')
          return
        }

        // 设置 canvas 尺寸
        const container = canvas.parentElement
        if (!container) return
        
        const dpr = window.devicePixelRatio || 1
        canvas.width = container.clientWidth * dpr
        canvas.height = container.clientHeight * dpr
        canvas.style.width = container.clientWidth + 'px'
        canvas.style.height = container.clientHeight + 'px'

        const ctx = canvas.getContext('2d')
        if (!ctx) {
          console.error('Could not get canvas context')
          return
        }

        if (!this.dailyMetrics) {
          console.warn('没有每日指标数据')
          return
        }

        const firstPredType = this.selectedTypes.find(type => 
          type !== '实测值' && this.dailyMetrics[type]
        )
        console.log('首个预测类型:', firstPredType)

        if (!firstPredType) {
          console.warn('没有找到有效的预测类型')
          return
        }

        const dateLabels = this.dailyMetrics[firstPredType]?.map(d => {
          const date = new Date(d.date)
          return `${date.getMonth()+1}/${date.getDate()}`
        }) || []
        console.log('日期标签:', dateLabels)

        if (dateLabels.length === 0) {
          console.warn('没有可用的日期标签')
          return
        }

        const datasets = Object.entries(this.dailyMetrics)
          .filter(([type]) => this.selectedTypes.includes(type) && type !== '实测值')
          .map(([type, data]) => {
            const values = data
              .map(d => {
                const value = this.currentMetric === 'acc' 
                  ? d[this.currentMetric] * 100 
                  : d[this.currentMetric]
                return Number.isFinite(value) ? value : null
              })
              .filter(v => v !== null)
            console.log(`${type} 的值:`, values)
            const avg = values.reduce((a, b) => a + b, 0) / values.length
            console.log(`${type} 的平均值:`, avg)

            return {
              label: `${type} (平均: ${avg.toFixed(2)}${this.currentMetric === 'acc' ? '%' : ''})`,
              data: values,
              borderColor: this.colors[type],
              backgroundColor: `${this.colors[type]}33`,
              tension: 0.3,
              pointRadius: 3,
              fill: false
            }
          })

        if (datasets.length === 0) {
          console.warn('没有数据集可以显示')
          return
        }

        console.log('准备的数据集:', datasets)

        const metric = {
          acc: { label: 'ACC (%)', min: 0, max: 100 },
          mae: { label: 'MAE (MW)', min: 0 },
          mse: { label: 'MSE (MW²)', min: 0 },
          rmse: { label: 'RMSE (MW)', min: 0 },
          k: { label: 'K值', min: -1, max: 1 },
          pe: { label: 'Pe (MW)', min: 0 }
        }[this.currentMetric]

        try {
          console.log('最终图表配置:', {
            labels: dateLabels,
            datasets: datasets.map(d => ({
              label: d.label,
              data: d.data,
              length: d.data.length
            }))
          })

          this.metricChart = new Chart(ctx, {
            type: 'line',
            data: {
              labels: dateLabels,
              datasets
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              animation: false,
              plugins: {
                legend: {
                  position: 'top',
                  labels: {
                    padding: 20,
                    font: { size: 13 }
                  }
                },
                title: {
                  display: true,
                  text: metric.label,
                  font: { size: 16 },
                  padding: 20
                }
              },
              scales: {
                x: {
                  display: true,
                  grid: { color: 'rgba(200,200,200,0.1)' },
                  ticks: { 
                    color: '#666',
                    maxRotation: 45,
                    minRotation: 45,
                    display: true
                  }
                },
                y: {
                  display: true,
                  beginAtZero: true,
                  min: metric.min,
                  max: metric.max,
                  grid: { color: 'rgba(200,200,200,0.1)' },
                  ticks: { 
                    color: '#666',
                    display: true,
                    callback: (value) => {
                      switch (this.currentMetric) {
                        case 'acc': return value.toFixed(1) + '%'
                        case 'mse': return value.toFixed(1) + ' MW²'
                        case 'k': return value.toFixed(2)
                        default: return value.toFixed(1) + ' MW'
                      }
                    }
                  }
                }
              }
            }
          })
          console.log('图表实例创建成功:', this.metricChart)
        } catch (error) {
          console.error('创建图表时出错:', error)
        }

        // 添加图表 resize 事件监听
        new ResizeObserver(() => {
          if (this.metricChart) {
            this.metricChart.resize()
          }
        }).observe(container)
      })
    },

    // 修改generateComparisonCSV方法，确保所有行都是数组
    generateComparisonCSV() {
        // 添加空值校验
        if (!this.exportData.comparison || 
            !this.exportData.comparison.rawTimestamps || 
            !this.exportData.comparison.datasets) {
            this.$message.warning('导出数据尚未准备好')
            return ''
        }

        const headers = ['时间戳', '实测值(MW)']
        // 添加类型存在性校验
        const predictionTypes = (this.selectedTypes || [])
            .filter(t => t !== '实测值' && this.exportData.comparison.datasets[t])

        predictionTypes.forEach(type => {
            headers.push(`${type}(MW)`)
        })

        // 安全访问实测值数据
        const actualData = this.exportData.comparison.datasets['实测值'] || []

        const dataRows = this.exportData.comparison.rawTimestamps.map((ts, index) => {
            // 将UTC时间转换为北京时间（UTC+8）
            const date = new Date(ts)
            const beijingDate = new Date(date.getTime() + 8 * 60 * 60 * 1000)
            
            // 格式化为 YYYY-MM-DD HH:mm:ss
            const formattedDate = 
                `${beijingDate.getUTCFullYear()}-` +
                `${(beijingDate.getUTCMonth() + 1).toString().padStart(2, '0')}-` +
                `${beijingDate.getUTCDate().toString().padStart(2, '0')} ` +
                `${beijingDate.getUTCHours().toString().padStart(2, '0')}:` +
                `${beijingDate.getUTCMinutes().toString().padStart(2, '0')}:` +
                `${beijingDate.getUTCSeconds().toString().padStart(2, '0')}`

            const row = [formattedDate]
            row.push(actualData[index] || '')
            
            predictionTypes.forEach(type => {
                const dataSet = this.exportData.comparison.datasets[type] || []
                row.push(dataSet[index] || '')
            })
            
            return row
        })

        // 修改指标数据提取部分
        const metricsHeader = ['\n评估指标', 'MAE', 'RMSE', 'ACC', 'K值', 'Pe']
        const metricsRows = (this.chartInstance?.data?.datasets || [])
            .filter(d => d.label && d.label.includes('('))
            .map(d => {
                // 调整正则表达式匹配模式
                const match = d.label.match(/(.*?)\s+\(MAE:\s+([\d.]+)\s+\|\s+RMSE:\s+([\d.]+)\s+\|\s+ACC:\s+([\d.]+)%\s+\|\s+K:\s+([\d.]+)\s+\|\s+Pe:\s+([\d.]+)\)/)
                return match ? [
                    match[1],  // 预测类型
                    match[2],  // MAE
                    match[3],  // RMSE
                    match[4],  // ACC
                    match[5],  // K
                    match[6]   // Pe
                ] : null
            })
            .filter(row => row) // 过滤无效项

        // 确保所有行都是有效数组
        const csvData = [
            headers,
            ...dataRows,
            metricsHeader,
            ...metricsRows
        ].filter(row => Array.isArray(row))

        return csvData
            .map(row => {
                // 确保每个单元格都是字符串
                const processedRow = row.map(cell => {
                    if (Array.isArray(cell)) return cell.join(',') // 处理嵌套数组
                    return typeof cell === 'string' ? cell : String(cell)
                })
                return processedRow.join(',')
            })
            .join('\n')
    },

    // 修复指标数据下载方法
    downloadMetricsCSV() {
      if (!this.exportData.metrics) {
        this.$message.warning('暂无可导出的指标数据')
        return
      }

      const headers = ['日期', '预测类型', 'ACC(%)', 'MAE(MW)', 'MSE(MW²)', 'RMSE(MW)', 'K值', 'Pe(MW)']
      const rows = []
      
      Object.entries(this.exportData.metrics).forEach(([type, days]) => {
        days.forEach(day => {
          rows.push([
            day.date,
            type,
            (day.acc * 100).toFixed(2),
            day.mae.toFixed(2),
            day.mse.toFixed(2),
            day.rmse.toFixed(2),
            day.k.toFixed(2),
            day.pe.toFixed(2)
          ])
        })
      })

      const csvContent = [headers, ...rows]
        .map(row => row.join(','))
        .join('\n')

      const blob = new Blob(["\ufeff" + csvContent], { type: 'text/csv;charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `每日评估指标_${new Date().toLocaleString().replace(/[/\s:]/g, '-')}.csv`
      link.click()
    },

    // 新增指标图表下载方法
    downloadMetricSVG() {
      const canvas = this.$refs.metricChart
      if (!canvas) {
        this.$message.warning('暂无可导出的指标图表')
        return
      }

      const svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}">
        <foreignObject width="100%" height="100%">
          <div xmlns="http://www.w3.org/1999/xhtml">
            <img src="${canvas.toDataURL('image/png')}" width="100%" height="100%"/>
          </div>
        </foreignObject>
      </svg>`

      const blob = new Blob([svgContent], { type: 'image/svg+xml' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `指标图表_${new Date().toLocaleString().replace(/[/\s:]/g, '-')}.svg`
      link.click()
    },

    // 下载CSV文件（修复正则表达式）
    downloadCSV() {
      if (!this.exportData.comparison) {
        this.$message.warning('暂无可导出的对比数据')
        return
      }

      const csvContent = this.generateComparisonCSV()
      const blob = new Blob(["\ufeff" + csvContent], { type: 'text/csv;charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `功率对比数据_${new Date().toLocaleString().replace(/[/\s:]/g, '-')}.csv`
      link.click()
    },

    // 下载SVG图像（修复正则表达式）
    downloadSVG() {
      const canvas = this.$refs.chartCanvas
      if (!canvas) {
        this.$message.warning('暂无可导出的图表')
        return
      }

      // 生成 SVG 内容
      const svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}">
          <foreignObject width="100%" height="100%">
              <div xmlns="http://www.w3.org/1999/xhtml">
                  <img src="${canvas.toDataURL('image/png')}" width="100%" height="100%"/>
              </div>
          </foreignObject>
      </svg>`

      // 创建 Blob 对象（修复未定义错误）
      const blob = new Blob([svgContent], { type: 'image/svg+xml' })
      
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `功率对比图表_${new Date().toLocaleString().replace(/[/\s:]/g, '-')}.svg`
      link.click()
    },
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

.time-picker-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  padding: 20px;  /* 统一内边距 */
}

.time-range-picker {
  display: flex;
  align-items: center;
  justify-content: center;  /* 水平居中 */
  gap: 16px;
  width: 100%;
}

/* 调整标签和时间选择器的容器 */
.time-picker-wrapper {
  display: flex;
  align-items: center;
  gap: 16px;
}

.type-checkbox-group {
  padding: 20px;
}

.label {
  display: flex;
  align-items: center;
  gap: 4px;
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

.daily-metrics-container {
  margin-top: 24px;
}

.metrics-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.metrics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.metrics-header h3 {
  margin: 0;
  color: #333;
}

.metric-buttons {
  display: flex;
  gap: 10px;
}

.metrics-chart-wrapper {
  height: 500px;
  min-height: 400px;
  position: relative;
  width: 100%;
  background: white;
  padding: 20px;
  overflow: hidden;
}

.metrics-chart-wrapper canvas {
  width: 100% !important;
  height: 100% !important;
  display: block !important;
}

@media (max-width: 768px) {
  .metrics-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .metric-buttons {
    flex-wrap: wrap;
  }
}

/* 添加下载按钮样式 */
.download-buttons {
  margin-left: 0;
}

.el-button-group .el-button {
  padding: 10px 15px;
}

@media (max-width: 768px) {
  .time-range-picker {
    flex-direction: column;
    gap: 12px;
  }
  
  .download-buttons {
    margin-left: 0;
    width: 100%;
  }
  
  .download-buttons .el-button {
    width: 100%;
    margin-top: 8px;
  }
}

/* 调整按钮组样式 */
.button-group {
  display: flex;
  align-items: center;
  justify-content: center;  /* 水平居中 */
  gap: 12px;
}

.download-buttons {
  display: flex;
  gap: 8px;
}

.download-buttons .el-button {
  padding: 8px 15px;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

/* 调整查询按钮样式 */
.el-button--primary {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
}

/* 响应式布局调整 */
@media (max-width: 1200px) {
  .time-range-picker {
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }

  .time-picker-wrapper {
    flex-direction: column;
    align-items: center;
  }

  .button-group {
    width: 100%;
    justify-content: center;
  }

  .download-buttons {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .download-buttons {
    grid-template-columns: 1fr;
  }

  .button-group {
    flex-direction: column;
  }

  .el-button--primary,
  .download-buttons .el-button {
    width: 100%;
  }
}
</style> 