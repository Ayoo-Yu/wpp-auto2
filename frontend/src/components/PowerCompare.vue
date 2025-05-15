<template>
  <div class="power-compare-container power-predict-container">
    <!-- 添加背景动画层 -->
    <div class="background-container">
      <div class="animated-background"></div>
    </div>

    <!-- 刷新按钮 -->
    <el-button 
      icon="Refresh" 
      circle 
      class="refresh-button"
      title="刷新页面"
      @click="refreshPage"
    ></el-button>

    <h1 class="page-title">数据可视化与下载</h1>

    <!-- 时间选择与配置区域 -->
    <div class="config-panel">
      <el-card class="merged-config-card"> 
        <!-- Row 1: Time Picker, Query Button, Download Buttons -->
        <div class="config-row config-row-1">
          <div class="time-picker-wrapper-outer">
            <span class="label">选择时间范围：</span>
            <el-date-picker
              v-model="timeRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              value-format="YYYY-MM-DD HH:mm:ss"
              class="time-range-picker-element" 
            />
          </div>
          <el-button-group class="quick-time-select-buttons" style="margin-left: 10px; margin-right: 10px;">
            <el-button type="info" plain size="small" @click="setQuickTimeRange('today')" :disabled="isQuickTimeSwitching">今日</el-button>
            <el-button type="info" plain size="small" @click="setQuickTimeRange('3d')" :disabled="isQuickTimeSwitching">近三天</el-button>
            <el-button type="info" plain size="small" @click="setQuickTimeRange('1w')" :disabled="isQuickTimeSwitching">近一周</el-button>
            <el-button type="info" plain size="small" @click="setQuickTimeRange('1m')" :disabled="isQuickTimeSwitching">近一个月</el-button>
          </el-button-group>
          <el-button 
            type="primary" 
            @click="fetchComparisonData"
            :loading="loading"
            class="query-button"
          >
            查询数据
          </el-button>
          <el-button-group class="download-buttons download-buttons-row1">
            <el-button 
              type="success" 
              @click="downloadCSV"
              :disabled="!exportData.comparison"
            >
              数据下载
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
            <el-button
              type="success"
              @click="showDailyMetricsAnalysis = !showDailyMetricsAnalysis"
            >
              {{ showDailyMetricsAnalysis ? '隐藏' : '显示' }}每日指标
            </el-button>
            <el-button
              type="success"
              @click="showQualificationRateAnalysis = !showQualificationRateAnalysis"
              :disabled="!qualificationRates || Object.keys(qualificationRates).length === 0"
            >
              {{ showQualificationRateAnalysis ? '隐藏' : '显示' }}合格率分析
            </el-button>
          </el-button-group>
        </div>

        <!-- Row 2: Type Select -->
        <div class="config-row config-row-2">
          <div class="type-checkbox-group type-checkbox-group-row2">
            <span class="label">选择展示类型：</span>
            <el-checkbox-group v-model="selectedTypes" class="type-selector-group">
              <el-checkbox label="实测值" />
              <el-checkbox label="超短期预测" />
              <el-checkbox label="短期预测" />
              <el-checkbox label="中期预测" />
              <el-checkbox label="短期风速预测" />
              <el-checkbox label="中期风速预测" />
            </el-checkbox-group>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 图表展示区域 -->
    <div class="chart-container" v-if="chartData">
      <div class="chart-wrapper" :key="chartKey">
        <canvas ref="chartCanvas" style="height: 70vh !important;"></canvas>
      </div>
    </div>

    <!-- 每日指标区域 -->
    <div class="daily-metrics-container" v-if="showDailyMetricsAnalysis && dailyMetrics">
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
          <canvas 
            ref="metricChart" 
            style="width: 100%; height: 100%; display: block;"
          ></canvas>
        </div>
      </el-card>
    </div>

    <!-- 数据提示区域 -->
    <div class="empty-data-container" v-if="!chartData">
      <el-card class="empty-data-card">
        <div class="empty-data-content">
          <el-icon class="empty-icon"><PieChart /></el-icon>
          <h3>暂无数据</h3>
          <p class="empty-text">请选择时间范围并点击查询数据按钮</p>
        </div>
      </el-card>
    </div>

    <!-- 合格率分析区域 -->
    <div class="qualification-container" v-if="showQualificationRateAnalysis && qualificationRates && Object.keys(qualificationRates).length > 0">
      <el-card class="qualification-card">
        <div class="qualification-header">
          <h3>预测合格率分析</h3>
        </div>
        <div class="qualification-content">
          <div v-for="(data, type) in qualificationRates" :key="type" class="qualification-item">
            <div class="qualification-type">
              <span class="type-label">{{ type }}</span>
              <span class="threshold-label">合格标准: K值 > {{ data.threshold }}</span>
            </div>
            <el-progress 
              :percentage="data.rate" 
              :color="getQualificationColor(data.rate)"
              :format="percent => `${percent.toFixed(1)}%`"
              :stroke-width="18"
            />
            <div class="qualification-details">
              <span>合格天数: {{ data.qualifiedDays }}/{{ data.totalDays }}</span>
            </div>
          </div>
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
import zoomPlugin from 'chartjs-plugin-zoom';
import axios from 'axios'

Chart.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  LineController,
  zoomPlugin // Register the zoom plugin
)

// Define Y-axis constants at a higher scope
const YAXIS_POWER = 'yPower';
const YAXIS_WINDSPEED = 'yWindSpeed';

export default {
  name: 'PowerCompare',
  data() {
    return {
      // API地址设置
      backendBaseUrl: window.location.hostname !== 'localhost' 
        ? `http://${window.location.hostname}:5000` 
        : 'http://localhost:5000',
      timeRange: [],
      selectedTypes: ['实测值', '超短期预测', '短期预测', '中期预测','短期风速预测','中期风速预测'],
      chartData: null,
      chartInstance: null,
      loading: false,
      wfcapacity: 453.5,
      currentMetric: 'acc',
      dailyMetrics: null,
      metricChart: null,
      colors: {
        '实测值': '#FF6B6B',
        '超短期预测': '#4ECDC4',
        '短期预测': '#45B7D1',
        '中期预测': '#96CEB4'
      },
      windSpeedColors: {
        '短期风速': '#FFD700',
        '中期风速': '#DA70D6',
      },
      exportData: {
        comparison: null,
        metrics: null
      },
      qualifiedThresholds: {
        '超短期预测': 0.65,
        '短期预测': 0.6,
        '中期预测': 0.4
      },
      qualificationRates: null,
      showDailyMetricsAnalysis: false,
      showQualificationRateAnalysis: false,
      selectedSupershortHorizon: ['average'],
      supershortHorizons: [
        { value: 'average', label: '平均值' },
        ...Array.from({ length: 16 }, (_, i) => ({
          value: `wp_pred${i + 2}`,
          label: `P${i + 1}`,
        })),
      ],
      chartKey: 0,
      isProcessingChart: false,
      isQuickTimeSwitching: false, // Flag for quick time range button cooldown
    }
  },
  mounted() {
    const today = new Date();
    const year = today.getFullYear();
    const month = (today.getMonth() + 1).toString().padStart(2, '0');
    const day = today.getDate().toString().padStart(2, '0');
    
    this.timeRange = [
      `${year}-${month}-${day} 00:00:00`,
      `${year}-${month}-${day} 23:59:59`,
    ];
    this.fetchComparisonData();
  },
  methods: {
    refreshPage() {
      window.location.reload();
    },
    async fetchComparisonData() {
      if (this.isProcessingChart) {
        this.$message.warning('正在处理上一个请求，请稍候...');
        return;
      }
      this.isProcessingChart = true;
      this.loading = true;

      if (!this.timeRange || this.timeRange.length !== 2) {
        this.$message.error('请选择完整的时间范围');
        this.loading = false; // Release loading state
        this.isProcessingChart = false; // Release lock
        return;
      }

      try {
        const payload = {
          start: this.timeRange[0],
          end: this.timeRange[1],
          types: this.selectedTypes,
          ...(this.selectedTypes.includes('超短期预测') && { supershort_horizon: 'average' })
        };

        const response = await axios.post(`${this.backendBaseUrl}/power-compare/data`, payload);
        await this.processChartData(response.data); 
      } catch (error) {
        this.$message.error('数据获取失败');
        console.error(error);
        this.chartData = null; 
      } finally {
        this.loading = false;
        this.isProcessingChart = false; // Ensure lock is released in finally
      }
    },

    async processChartData(apiData) {
      try {
          console.log('ProcessChartData - 原始API数据:', apiData);

          // 提前处理 apiData 为空或无效的情况
          if (!apiData || (typeof apiData === 'object' && Object.keys(apiData).length === 0)) {
              console.warn("ProcessChartData - apiData 无效或为空, 将清空图表并显示无数据提示。");
              this.chartData = null; // 这将触发 v-if="!chartData" 显示"暂无数据"
              if (this.chartInstance) {
                  console.log('ProcessChartData - 销毁因空数据产生的旧主图表实例');
                  this.chartInstance.destroy();
                  this.chartInstance = null;
              }
              // 如果指标图表也依赖于此，也需要清空
              if (this.showDailyMetricsAnalysis) {
                  this.dailyMetrics = null; // 清空指标数据
                  await this.$nextTick(); // 等待 DOM 更新（如果 metricChart 的 canvas 依赖 v-if）
                  this.updateMetricChart(); // updateMetricChart 内部会处理 dailyMetrics 为 null 的情况
              }
              this.exportData.comparison = null;
              this.exportData.metrics = null;
              return; // 处理完毕，提前返回
          }

          this.chartData = apiData; 

          await this.$nextTick(); 

          if (this.chartInstance) {
            console.log('ProcessChartData - 销毁旧的主图表实例:', this.chartInstance.id);
            this.chartInstance.destroy();
            this.chartInstance = null;
          }

          this.chartKey++;
          console.log('ProcessChartData - chartKey incremented to:', this.chartKey);

          await this.$nextTick(); 
          console.log('ProcessChartData - $nextTick after incrementing chartKey');

          const canvasEl = this.$refs.chartCanvas;
          if (!canvasEl) {
            console.error('ProcessChartData - 主图表 Canvas 元素 (this.$refs.chartCanvas) 未找到!');
            return;
          }
          
          const ctx = canvasEl.getContext('2d');
          if (!ctx) {
            console.error('ProcessChartData - 获取主图表 Canvas 的 2D 上下文失败!');
            return;
          }
          
          // ... (rest of the processChartData method, including calculateDailyMetrics, prepareChartJsDataForMainChart, new Chart, updateMetricChart call)
          // The following is a placeholder for the rest of your processChartData, ensure the actual content is there.
          console.log('ProcessChartData - 开始计算每日指标');
          this.dailyMetrics = this.calculateDailyMetrics(apiData); 
          console.log('ProcessChartData - 每日指标计算结果:', this.dailyMetrics);

          const { labels, datasets: chartJSDatasets, sortedTimestamps } = this.prepareChartJsDataForMainChart(apiData);
          console.log('ProcessChartData - 为主图表准备的 Labels:', labels);
          console.log('ProcessChartData - 为主图表准备的 Datasets:', chartJSDatasets);

          if (labels.length === 0 && chartJSDatasets.length === 0 && Object.keys(apiData).length > 0) {
              console.warn("ProcessChartData - API有数据但处理后图表数据为空,检查prepareChartJsDataForMainChart逻辑");
          }

          try {
        this.chartInstance = new Chart(ctx, {
          type: 'line',
          data: {
                labels: labels,
                datasets: chartJSDatasets
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            plugins: {
              legend: {
                position: 'top',
                labels: {
                  padding: 20,
                  font: { size: 13 },
                  usePointStyle: true,
                  pointStyle: 'line'
                }
              },
              tooltip: { 
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) {
                            label += ': ';
                        }
                        if (context.parsed.y !== null) {
                            label += context.parsed.y.toFixed(2);
                            if (context.dataset.yAxisID === YAXIS_POWER) {
                                label += ' MW';
                            } else if (context.dataset.yAxisID === YAXIS_WINDSPEED) {
                                label += ' m/s'; 
                            }
                        }
                        return label;
                    }
                }
                  },
                  zoom: { 
                    pan: {
                      enabled: true,
                      mode: 'x',
                      threshold: 5,
                    },
                    zoom: {
                      wheel: {
                        enabled: true,
                      },
                      pinch: {
                        enabled: true
                      },
                      mode: 'x',
                      drag: {
                        enabled: true,
                        backgroundColor: 'rgba(0,123,255,0.25)'
                      }
                    },
                    limits: {
                    },
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
              [YAXIS_POWER]: { 
                type: 'linear',
                display: true,
                position: 'left',
                beginAtZero: true,
                suggestedMax: this.wfcapacity * 1.1, 
                title: {
                  display: true,
                  text: '功率 (MW)',
                  color: '#666'
                },
                grid: { color: 'rgba(255,255,255,0.1)' },
                ticks: { color: '#666' }
              },
              [YAXIS_WINDSPEED]: { 
                type: 'linear',
                    display: chartJSDatasets.some(ds => ds.yAxisID === YAXIS_WINDSPEED), 
                position: 'right',
                beginAtZero: true,
                suggestedMax: 30, 
                title: {
                  display: true,
                  text: '风速 (m/s)', 
                  color: '#666'
                },
                grid: { 
                  drawOnChartArea: false, 
                },
                ticks: { color: '#666' }
              }
            }
          }
            });
            console.log('ProcessChartData - 新的主图表实例创建成功:', this.chartInstance.id);
          } catch (e) {
            console.error("ProcessChartData - 创建主图表实例时出错:", e);
            return;
          }

      this.$nextTick(() => {
            if (this.showDailyMetricsAnalysis && this.dailyMetrics) {
              console.log('ProcessChartData - 调用 updateMetricChart');
              this.updateMetricChart();
            }
          });

          const exportComparisonDatasets = {};
          chartJSDatasets.forEach(dataset => {
              let cleanKey = dataset.label;
              const matchMetrics = dataset.label.match(/^(.*?)\s*\(/); 
              if (matchMetrics && matchMetrics[1]) {
                  cleanKey = matchMetrics[1].trim();
              }
          if (dataset.yAxisID === YAXIS_WINDSPEED) {
                  cleanKey = cleanKey.replace(' (右轴)', '').trim();
          }
              exportComparisonDatasets[cleanKey] = dataset.data;
      });

      this.exportData.comparison = {
        labels: labels,
        rawTimestamps: sortedTimestamps,
            datasets: exportComparisonDatasets
          };
          this.exportData.metrics = this.dailyMetrics;
          console.log('ProcessChartData - 导出数据已准备:', this.exportData);

      } catch(e) {
          console.error("Error in processChartData:", e);
      } 
    },

    // 辅助方法：为主要对比图表准备 Chart.js 数据格式
    prepareChartJsDataForMainChart(apiData) {
      const datasets = [];
      const powerColors = {
        '实测值': '#FF6B6B',
        '超短期预测': this.colors['超短期预测'], // 确保 this.colors 定义了这些
        '短期预测': this.colors['短期预测'],
        '中期预测': this.colors['中期预测']
      };
      const windSpeedColors = this.windSpeedColors; // 确保 this.windSpeedColors 定义了这些

      let timestamps = new Set();
      if (apiData && typeof apiData === 'object' && Object.keys(apiData).length > 0) {
        Object.values(apiData).forEach(seriesArray => {
          if (Array.isArray(seriesArray)) {
            seriesArray.forEach(v => {
              if (v && v.timestamp) timestamps.add(v.timestamp);
            });
          }
        });
      } else {
          console.warn("prepareChartJsDataForMainChart: apiData 无效或为空, 返回空图表数据");
          return { labels: [], datasets: [], sortedTimestamps: [] };
      }


      const sortedTimestamps = Array.from(timestamps)
        .map(ts => new Date(ts).getTime())
        .sort((a, b) => a - b)
        .map(ts => new Date(ts).toISOString());

      const labels = sortedTimestamps.map(ts => {
        const date = new Date(ts);
        return `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2,'0')}`;
      });

      // --- 处理功率数据 ---
      if (apiData['实测值'] && Array.isArray(apiData['实测值'])) {
        const actualMap = new Map(apiData['实测值'].map(v => [
          new Date(v.timestamp).toISOString(),
          v.power
        ]));
        datasets.push({
          label: '实测值',
          data: sortedTimestamps.map(ts => actualMap.get(ts) === undefined ? null : actualMap.get(ts)),
          borderColor: powerColors['实测值'],
          backgroundColor: `${powerColors['实测值']}33`,
          tension: 0.3,
          pointRadius: 3,
          spanGaps: true,
          yAxisID: YAXIS_POWER
        });
      }

      const predictionKeys = ['超短期预测', '短期预测', '中期预测'];
      const selectedPredictionTypes = predictionKeys.filter(type => this.selectedTypes.includes(type) && apiData[type] && Array.isArray(apiData[type]));

      selectedPredictionTypes.forEach(type => {
        const predictedMap = new Map(apiData[type].map(v => [
          new Date(v.timestamp).toISOString(),
          v.power
        ]));

        let metricsTextLabel = type;
        // 'average' 是默认的，但如果 selectedSupershortHorizon 可以是其他值，需要处理
        const horizon = (type === '超短期预测' && this.selectedSupershortHorizon && this.selectedSupershortHorizon.length > 0)
                            ? this.selectedSupershortHorizon.join(', ') : 'average';
        if (type === '超短期预测') {
            metricsTextLabel = `${type} (${horizon})`;
        }

        if (apiData['实测值'] && Array.isArray(apiData['实测值']) && apiData[type] && Array.isArray(apiData[type])) {
          const actualValuesForOverall = [];
          const predictedValuesForOverall = [];
          // 确保只比较有对应实测值的预测点
          apiData[type].forEach(pred => {
            const predTime = new Date(pred.timestamp).getTime();
            const actualPoint = apiData['实测值'].find(
              act => new Date(act.timestamp).getTime() === predTime
            );
            if (actualPoint && typeof pred.power === 'number' && typeof actualPoint.power === 'number') {
              predictedValuesForOverall.push(pred.power);
              actualValuesForOverall.push(actualPoint.power);
            }
          });

          if (predictedValuesForOverall.length > 0 && actualValuesForOverall.length === predictedValuesForOverall.length) {
            const overallMetrics = this.calculateMetrics(actualValuesForOverall, predictedValuesForOverall);
            metricsTextLabel = `${metricsTextLabel} (MAE: ${overallMetrics.mae.toFixed(1)} | RMSE: ${overallMetrics.rmse.toFixed(1)} | ACC: ${(overallMetrics.acc * 100).toFixed(1)}% | K: ${overallMetrics.k.toFixed(2)} | Pe: ${overallMetrics.pe.toFixed(1)})`;
          } else {
            console.warn(`prepareChartJsDataForMainChart: 类型 ${type} 计算整体指标时数据不足或不匹配`);
          }
        }
        
        datasets.push({
          label: metricsTextLabel,
          data: sortedTimestamps.map(ts => predictedMap.get(ts) === undefined ? null : predictedMap.get(ts)),
          borderColor: powerColors[type],
          backgroundColor: `${powerColors[type]}33`,
          tension: 0.3,
          pointRadius: 3,
          spanGaps: true,
          yAxisID: YAXIS_POWER
        });
      });

      // --- 处理风速数据 ---
      // 你的 selectedTypes 包含 "短期风速预测", "中期风速预测"
      // 但 apiData 的 key 可能是 "短期风速", "中期风速"
      const windSpeedApiKeys = {
          '短期风速预测': '短期风速',
          '中期风速预测': '中期风速'
      };
      const selectedWindSpeedTypes = Object.keys(windSpeedApiKeys)
                                      .filter(type => this.selectedTypes.includes(type) && apiData[windSpeedApiKeys[type]] && Array.isArray(apiData[windSpeedApiKeys[type]]));

      selectedWindSpeedTypes.forEach(selectedTypeKey => { // e.g., "短期风速预测"
        const apiKey = windSpeedApiKeys[selectedTypeKey]; // e.g., "短期风速"
        const wsMap = new Map(apiData[apiKey].map(v => [
            new Date(v.timestamp).toISOString(),
            v.wind_speed
        ]));
        datasets.push({
            label: `${apiKey} (右轴)`, // 使用 apiKey "短期风速" 作为图例标签基础
            data: sortedTimestamps.map(ts => wsMap.get(ts) === undefined ? null : wsMap.get(ts)),
            borderColor: windSpeedColors[apiKey], // 使用 apiKey "短期风速"
            backgroundColor: `${windSpeedColors[apiKey]}33`,
            tension: 0.4,
            pointRadius: 2,
            borderDash: [5, 5],
            spanGaps: true,
            yAxisID: YAXIS_WINDSPEED
        });
      });
      
      return { labels, datasets, sortedTimestamps };
    },

    calculateMetrics(actual, predicted) {
      const threshold = 0.2 * this.wfcapacity
      
      const mae = predicted.reduce((sum, p, i) => sum + Math.abs(p - actual[i]), 0) / predicted.length
      
      const mse = predicted.reduce((sum, p, i) => sum + Math.pow(p - actual[i], 2), 0) / predicted.length
      const rmse = Math.sqrt(mse)
      
      const acc = 1 - rmse / this.wfcapacity
      
      const pe = acc < 0.83 ? (0.83 - acc) * this.wfcapacity : 0
      
      const m_values = predicted.map((p, i) => {
        const actualVal = Math.max(actual[i], threshold)
        return Math.pow((p - actual[i]) / actualVal, 2)
      })
      const k = 1 - Math.sqrt(m_values.reduce((sum, v) => sum + v, 0) / m_values.length)
      
      return { mae, mse, rmse, acc, k, pe }
    },

    calculateDailyMetrics(data) {
      console.log('计算每日指标的输入数据:', data)
      if (!data['实测值']) {
        console.warn('没有实测值数据，无法计算评估指标')
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
            const threshold = this.qualifiedThresholds[type] || 0
            const isQualified = metrics.k > threshold
            return { date, ...metrics, isQualified }
          })
          .sort((a, b) => new Date(a.date) - new Date(b.date))
      })

      this.calculateQualificationRates(dailyMetrics)

      return dailyMetrics
    },

    calculateQualificationRates(dailyMetrics) {
      const qualificationRates = {}
      
      Object.entries(dailyMetrics).forEach(([type, metrics]) => {
        const qualifiedDays = metrics.filter(day => day.isQualified)
        const rate = metrics.length > 0 ? (qualifiedDays.length / metrics.length) * 100 : 0
        qualificationRates[type] = {
          totalDays: metrics.length,
          qualifiedDays: qualifiedDays.length,
          rate: rate,
          threshold: this.qualifiedThresholds[type]
        }
      })
      
      this.qualificationRates = qualificationRates
    },

    updateMetricChart() {
      console.log('UpdateMetricChart - 开始更新指标图表');
      
      if (this.metricChart) {
        console.log('UpdateMetricChart - 销毁旧的指标图表实例');
        this.metricChart.destroy();
        this.metricChart = null;
      }

      // 确保在 DOM 更新后执行
      this.$nextTick(() => {
        const canvas = this.$refs.metricChart;
        if (!canvas) {
          console.error('UpdateMetricChart - 指标图表 Canvas 元素 (this.$refs.metricChart) 未找到');
          return;
        }
        console.log('UpdateMetricChart - 获取到指标图表 Canvas 元素:', canvas);

        const container = canvas.parentElement;
        if (!container) {
            console.error('UpdateMetricChart - 指标图表 Canvas 的父容器未找到');
            return;
        }
        
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.floor(container.clientWidth * dpr);
        canvas.height = Math.floor(container.clientHeight * dpr);

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          console.error('UpdateMetricChart - 获取指标图表 Canvas 的 2D 上下文失败');
          return;
        }
        console.log('UpdateMetricChart - 获取到指标图表 Canvas 的 2D 上下文:', ctx);

        if (!this.dailyMetrics || Object.keys(this.dailyMetrics).length === 0) {
          console.warn('UpdateMetricChart - 没有每日指标数据可供显示');
          ctx.clearRect(0, 0, canvas.width, canvas.height); 
          ctx.font = "16px Arial";
          ctx.fillStyle = "#888";
          ctx.textAlign = "center";
          ctx.fillText("暂无指标数据", canvas.width / 2, canvas.height / 2);
          return;
        }

        const { labels: dateLabels, datasets: metricDatasets } = this.prepareMetricChartData(); 
        
        if (!dateLabels || dateLabels.length === 0 || !metricDatasets || metricDatasets.length === 0) {
            console.warn('UpdateMetricChart - 为指标图表准备的数据为空');
             ctx.clearRect(0, 0, canvas.width, canvas.height);
             ctx.font = "16px Arial";
             ctx.fillStyle = "#888";
             ctx.textAlign = "center";
             ctx.fillText("所选指标无数据", canvas.width / 2, canvas.height / 2);
            return;
        }

        const metricConfig = {
          acc: { label: 'ACC (%)', min: 0, max: 100 },
          mae: { label: 'MAE (MW)', min: 0 },
          mse: { label: 'MSE (MW²)', min: 0 },
          rmse: { label: 'RMSE (MW)', min: 0 },
          k: { label: 'K值', min: -1, max: 1 },
          pe: { label: 'Pe (MW)', min: 0 }
        }[this.currentMetric];

          const qualificationLinePlugin = {
            id: 'qualificationLine',
            beforeDraw: (chart) => {
              if (this.currentMetric === 'k') {
                const pluginCtx = chart.ctx; // Use different variable name
                const yAxis = chart.scales.y;
                const chartArea = chart.chartArea;

                Object.entries(this.qualifiedThresholds).forEach(([type, threshold]) => {
                  if (this.selectedTypes.includes(type)) {
                    const y = yAxis.getPixelForValue(threshold);
                    pluginCtx.save(); 
                    pluginCtx.beginPath();
                    pluginCtx.moveTo(chartArea.left, y);
                    pluginCtx.lineTo(chartArea.right, y);
                    pluginCtx.lineWidth = 1;
                    pluginCtx.strokeStyle = `${this.colors[type]}99`;
                    pluginCtx.setLineDash([5, 5]);
                    pluginCtx.stroke();
                    
                    pluginCtx.textAlign = 'left';
                    pluginCtx.textBaseline = 'bottom';
                    pluginCtx.fillStyle = this.colors[type];
                    pluginCtx.font = '12px Arial';
                    pluginCtx.fillText(`${type}合格线: K > ${threshold}`, chartArea.left + 10, y - 2);
                    pluginCtx.restore();
                  }
                })
              }
            }
          };

        try {
          this.metricChart = new Chart(ctx, {
            type: 'line',
            data: {
              labels: dateLabels,
              datasets: metricDatasets
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
                  text: metricConfig.label,
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
                  min: metricConfig.min,
                  max: metricConfig.max,
                  grid: { color: 'rgba(200,200,200,0.1)' },
                  ticks: { 
                    color: '#666',
                    display: true,
                    callback: (value) => {
                      switch (this.currentMetric) {
                        case 'acc': return value.toFixed(1) + '%';
                        case 'mse': return value.toFixed(1) + ' MW²';
                        case 'k': return value.toFixed(2);
                        default: return value.toFixed(1) + ' MW';
                      }
                    }
                  }
                }
              }
            },
            plugins: [qualificationLinePlugin]
          });
          console.log('UpdateMetricChart - 指标图表实例创建成功:', this.metricChart.id);
        } catch (error) {
          console.error('UpdateMetricChart - 创建指标图表时出错:', error);
        }
      });
    },

    prepareMetricChartData() {
        if (!this.dailyMetrics) return { labels: [], datasets: [] };

        const firstPredTypeWithData = this.selectedTypes.find(type =>
            type !== '实测值' && this.dailyMetrics[type] && this.dailyMetrics[type].length > 0
        );

        if (!firstPredTypeWithData) return { labels: [], datasets: [] };

        const dateLabels = this.dailyMetrics[firstPredTypeWithData].map(d => {
            const date = new Date(d.date);
            return `${date.getMonth() + 1}/${date.getDate()}`;
        });

        const datasets = Object.entries(this.dailyMetrics)
            .filter(([type, data]) => 
                this.selectedTypes.includes(type) && 
                type !== '实测值' && 
                data && data.length > 0 
            )
            .map(([type, data]) => {
                const values = data.map(d => {
                    const value = this.currentMetric === 'acc' ? d[this.currentMetric] * 100 : d[this.currentMetric];
                    return Number.isFinite(value) ? value : null; 
                });
                
                const finiteValues = values.filter(v => v !== null);
                const avg = finiteValues.length > 0 ? finiteValues.reduce((a, b) => a + b, 0) / finiteValues.length : 0;

                return {
                    label: `${type} (平均: ${avg.toFixed(2)}${this.currentMetric === 'acc' ? '%' : ''})`,
                    data: values, 
                    borderColor: this.colors[type],
                    backgroundColor: `${this.colors[type]}33`,
                    tension: 0.3,
                    pointRadius: 3,
                    fill: false,
                    spanGaps: true 
                };
            })
            .filter(ds => ds.data.some(val => val !== null)); 

        return { labels: dateLabels, datasets };
    },
    
    // ... other methods like generateComparisonCSV, downloadMetricsCSV, downloadSVG, downloadMetricSVG, getQualificationColor, setQuickTimeRange etc.
    // Ensure they are still present
    generateComparisonCSV() {
        if (!this.exportData.comparison || 
            !this.exportData.comparison.rawTimestamps || 
            !this.exportData.comparison.datasets) {
            this.$message.warning('导出数据尚未准备好')
            return ''
        }

        const headers = ['时间戳'];
        const dataKeys = []; 

        if (this.selectedTypes.includes('实测值') && this.exportData.comparison.datasets['实测值']) {
            headers.push('实测值(MW)');
            dataKeys.push('实测值');
        }
        
        const selectedPowerPredictionTypes = (this.selectedTypes || [])
            .filter(type => { 
                if (type === '实测值' || type.includes('风速')) return false;
                
                let keyToFindPrefix = type; 
                if (type === '超短期预测' && this.selectedSupershortHorizon.length > 0) {
                    keyToFindPrefix = `${type} (${this.selectedSupershortHorizon.join(', ')})`; 
                }
                return Object.keys(this.exportData.comparison.datasets).some(exportKey => exportKey.startsWith(keyToFindPrefix));
            });

        selectedPowerPredictionTypes.forEach(type => { 
            let csvHeaderName = type; 
            if (type === '超短期预测' && this.selectedSupershortHorizon.length > 0) {
                csvHeaderName = `${type} (${this.selectedSupershortHorizon.join(', ')})`; 
            }
            headers.push(`${csvHeaderName}(MW)`); 

            const actualDatasetKey = Object.keys(this.exportData.comparison.datasets)
                                       .find(k => k.startsWith(csvHeaderName)); 
            if (actualDatasetKey) {
                dataKeys.push(actualDatasetKey);
            } else {
                console.warn(`CSV Export: Could not find dataset key for power type: ${csvHeaderName}`);
                dataKeys.push(csvHeaderName); 
            }
        });

        const selectedWindSpeedTypes = (this.selectedTypes || [])
            .filter(type => { 
                if (!type.includes('风速预测')) return false;
                const keyToFind = type.replace('预测', ''); 
                return !!this.exportData.comparison.datasets[keyToFind];
            });

        selectedWindSpeedTypes.forEach(type => { 
            const csvHeaderName = type.replace('预测', ''); 
            headers.push(`${csvHeaderName}(m/s)`); 
            dataKeys.push(csvHeaderName); 
        });

        const dataRows = this.exportData.comparison.rawTimestamps.map((ts, index) => {
            const date = new Date(ts);
            const beijingDate = new Date(date.getTime() + 8 * 60 * 60 * 1000);
            const formattedDate = 
                `${beijingDate.getUTCFullYear()}-` +
                `${(beijingDate.getUTCMonth() + 1).toString().padStart(2, '0')}-` +
                `${beijingDate.getUTCDate().toString().padStart(2, '0')} ` +
                `${beijingDate.getUTCHours().toString().padStart(2, '0')}:` +
                `${beijingDate.getUTCMinutes().toString().padStart(2, '0')}:` +
                `${beijingDate.getUTCSeconds().toString().padStart(2, '0')}`;

            const row = [formattedDate];
            dataKeys.forEach(key => { 
                const dataSet = this.exportData.comparison.datasets[key] || [];
                const value = dataSet[index];
                row.push(value !== undefined && value !== null ? Number(value).toFixed(2) : '');
            });
            return row;
        });

        const csvData = [
            headers,
            ...dataRows,
        ];

        return csvData
            .filter(row => Array.isArray(row))
            .map(row => {
                const processedRow = row.map(cell => {
                    if (Array.isArray(cell)) return cell.join(',');
                    return typeof cell === 'string' ? cell : String(cell);
                });
                return processedRow.join(',');
            })
            .join('\n');
    },

    downloadMetricsCSV() {
      if (!this.exportData.metrics) {
        this.$message.warning('暂无可导出的指标数据')
        return
      }

      const headers = ['日期', '预测类型', 'ACC(%)', 'MAE(MW)', 'MSE(MW²)', 'RMSE(MW)', 'K值', 'Pe(MW)', '合格标准', '是否合格']
      const rows = []
      
      Object.entries(this.exportData.metrics).forEach(([type, days]) => {
        const threshold = this.qualifiedThresholds[type] || 0
        days.forEach(day => {
          rows.push([
            day.date,
            type,
            (day.acc * 100).toFixed(2),
            day.mae.toFixed(2),
            day.mse.toFixed(2),
            day.rmse.toFixed(2),
            day.k.toFixed(2),
            day.pe.toFixed(2),
            `K值 > ${threshold}`,
            day.isQualified ? '是' : '否'
          ])
        })
      })

      if (this.qualificationRates) {
        rows.push([])
        rows.push(['合格率汇总'])
        rows.push(['预测类型', '合格标准', '合格天数', '总天数', '合格率(%)'])
        
        Object.entries(this.qualificationRates).forEach(([type, data]) => {
          rows.push([
            type,
            `K值 > ${data.threshold}`,
            data.qualifiedDays,
            data.totalDays,
            data.rate.toFixed(1)
          ])
        })
      }

      const csvContent = [headers, ...rows]
        .map(row => row.join(','))
        .join('\n')

      const blob = new Blob(["\ufeff" + csvContent], { type: 'text/csv;charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `每日评估指标_${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }).replace(/[/\s:]/g, '-')}.csv`
      link.click()
    },

    downloadSVG() {
      const canvas = this.$refs.chartCanvas
      if (!canvas) {
        this.$message.warning('暂无可导出的图表')
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
      link.download = `功率对比图表_${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }).replace(/[/\s:]/g, '-')}.svg`
      link.click()
    },

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
      link.download = `指标图表_${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }).replace(/[/\s:]/g, '-')}.svg`
      link.click()
    },

    getQualificationColor(rate) {
      if (rate >= 80) return '#4CAF50';
      if (rate >= 60) return '#FFC107';
      return '#F44336';
    },

    setQuickTimeRange(period) {
      if (this.isQuickTimeSwitching) {
        this.$message.warning('请勿频繁操作快速选择按钮，请等待5秒...');
        return;
      }
      this.isQuickTimeSwitching = true;

      const endDate = new Date();
      let startDate = new Date();
      
      endDate.setHours(23, 59, 59, 999);
      startDate.setHours(0, 0, 0, 0);

      switch (period) {
        case 'today': {
          break;
        }
        case '3d':{
          startDate.setDate(endDate.getDate() - 2); 
          break;
        }
        case '1w':{
          startDate.setDate(endDate.getDate() - 6); 
          break;
        }
        case '1m': {
            startDate = new Date(endDate);
          startDate.setMonth(endDate.getMonth() - 1);
             startDate.setHours(0,0,0,0); // ensure time is reset
             // If original day was 31st and prev month has 30, it rolls.
             // Check if we rolled into the *same* month as endDate by going back then forward for month day
             const checkStartDate = new Date(endDate);
             checkStartDate.setMonth(endDate.getMonth() -1);
             if (checkStartDate.getMonth() === endDate.getMonth()) { // e.g. Mar 31 to Feb rolled to Mar 3
                 startDate = new Date(endDate.getFullYear(), endDate.getMonth(), 1); // Beginning of current month
                 startDate.setDate(0); // End of previous month
                 startDate.setHours(0,0,0,0);
           } else {
                // If day doesn't exist in prev month (e.g. Mar 31st -> Feb 31st doesn't exist)
                // it auto-adjusts. e.g. Mar 31st -> March 3rd (if Feb has 28 days).
                // We want it to be Feb 28th.
                // So, if startDate's month after setMonth is not (endDate.getMonth() - 1 + 12) % 12
                // it means it rolled over.
                const targetMonth = (endDate.getMonth() - 1 + 12) % 12;
                if (startDate.getMonth() !== targetMonth) {
                    // It rolled. Set to last day of target month.
                    startDate = new Date(endDate.getFullYear(), targetMonth + 1, 0); // day 0 of next month is last day of targetMonth
                    startDate.setHours(0,0,0,0);
                }
             }
          break;
        }
        case '3m':{
          startDate = new Date(endDate);
          startDate.setMonth(endDate.getMonth() - 3);
          startDate.setHours(0,0,0,0);
          // Similar month-end/roll-over logic as '1m' might be needed if very precise "calendar 3 months"
          // For simplicity, this will be "date X, 3 months ago"
          break;
        }
        case '6m':{ 
          startDate = new Date(endDate);
          startDate.setMonth(endDate.getMonth() - 6);
          startDate.setHours(0,0,0,0);
          break;
        }
        case '1y':{
          startDate = new Date(endDate);
          startDate.setFullYear(endDate.getFullYear() - 1);
          startDate.setHours(0,0,0,0);
          break;
        }
        default:
          this.$message.error('无效的快速选择周期');
          return;
      }
      startDate.setHours(0,0,0,0);


      const formatDateVal = (date) => {
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
      };

      this.timeRange = [
        `${formatDateVal(startDate)} 00:00:00`,
        `${formatDateVal(endDate)} 23:59:59`,
      ];
      this.fetchComparisonData();

      setTimeout(() => {
        this.isQuickTimeSwitching = false;
      }, 5000); // 5-second cooldown
    },
  },
  watch: {
    showDailyMetricsAnalysis(newValue) {
      if (newValue) { 
        this.$nextTick(() => { 
          if (this.dailyMetrics) { 
            this.updateMetricChart();
          } else {
            console.log("showDailyMetricsAnalysis changed to true, but dailyMetrics is still null/empty. Metric chart not updated yet.");
          }
        });
      } else if (this.metricChart) { 
          this.metricChart.destroy();
          this.metricChart = null;
      }
    },
    dailyMetrics(newMetrics) {
        if (this.showDailyMetricsAnalysis && newMetrics && Object.keys(newMetrics).length > 0) {
            this.$nextTick(() => {
                this.updateMetricChart();
            });
        }
    },
    // It might be beneficial to also watch `currentMetric` if changing it should
    // always redraw the metric chart, even if `dailyMetrics` itself hasn't changed.
    currentMetric() {
        if (this.showDailyMetricsAnalysis && this.dailyMetrics && Object.keys(this.dailyMetrics).length > 0) {
            this.$nextTick(() => {
                this.updateMetricChart();
            });
        }
    }
  },

  beforeUnmount() {
    if (this.chartInstance) {
      this.chartInstance.destroy();
      this.chartInstance = null;
    }
    if (this.metricChart) {
      this.metricChart.destroy();
      this.metricChart = null;
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

.refresh-button {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000; /*确保在其他元素之上*/
  background-color: rgba(255, 255, 255, 0.8) !important; /* 确保背景颜色不被全局样式覆盖 */
  border: 1px solid #dcdfe6 !important; /* 添加边框以增加可见性 */
  color: #606266 !important; /* 图标颜色 */
}

.refresh-button:hover {
  background-color: rgba(240, 240, 240, 0.9) !important;
  border-color: #c0c4cc !important;
  color: #303133 !important;
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
  margin-bottom: 24px;
}

.merged-config-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px; /* Consistent gap between rows */
}

.config-row {
  display: flex;
  align-items: center; 
  gap: 16px; 
  flex-wrap: wrap; 
}

/* Row 1: Time Picker, Query Button, Download Buttons */
.config-row-1 {
  /* justify-content: space-between; */ /* Let items flow naturally with gaps */
}

.config-row-1 .time-picker-wrapper-outer {
  display: flex;
  align-items: center;
  gap: 8px; 
}

.time-range-picker-element {
  min-width: 300px; /* Give date picker enough space */
}

.config-row-1 .query-button {
  /* margin-left: auto; */ /* Removed to keep it next to picker */
}

.download-buttons-row1 {
  margin-left: 16px; /* Add some space if query button is not pushing it far enough */
  /* Or use flex-grow on an element or justify-content on parent if more complex spacing is needed */
}

/* Row 2: Type Select */
.config-row-2 .type-checkbox-group-row2 {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%; /* Allow it to take full width for its checkboxes */
}

/* Row 3: Horizon Select */
.config-row-3 .horizon-select-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%; /* Allow it to take full width for its checkboxes */
}

/* General styling for checkbox groups within rows */
.type-selector-group, .horizon-selector-group {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 15px; /* row-gap column-gap */
}

.type-selector-group .el-checkbox,
.horizon-selector-group .el-checkbox {
  margin-right: 0px !important; /* Override Element Plus default if any */
  margin-left: 0 !important; 
}

/* Label styling remains the same */
.label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #333;
  font-weight: 500;
  white-space: nowrap;
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

.el-button--primary {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
}

.qualification-container {
  margin-top: 24px;
}

.qualification-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  padding: 20px;
}

.qualification-header {
  margin-bottom: 20px;
}

.qualification-header h3 {
  margin: 0;
  color: #333;
}

.qualification-content {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.qualification-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.qualification-type {
  margin-bottom: 10px;
}

.type-label {
  font-weight: 500;
}

.threshold-label {
  color: #909399;
}

.qualification-details {
  margin-top: 10px;
}

.daily-qualification-table {
  margin-top: 20px;
}

.daily-qualification-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.big-item {
  flex: 1 0 100%;
  margin-bottom: 20px;
  background-color: rgba(255, 255, 255, 0.8);
  border-radius: 12px;
  padding: 15px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.qualification-chart {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.qualification-type {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
}

.type-label {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.threshold-label {
  padding: 4px 10px;
  background: #f5f7fa;
  border-radius: 12px;
  font-size: 14px;
}

.qualification-details {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
  font-size: 14px;
  color: #666;
}

.daily-qualification-table {
  margin-top: 30px;
  background-color: rgba(255, 255, 255, 0.8);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.daily-qualification-table h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
  font-size: 16px;
}

.daily-qualification-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  color: #333;
  font-weight: 600;
}

:deep(.el-progress-bar__inner) {
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-progress) {
  margin-bottom: 5px;
}

:deep(.el-progress-bar__outer) {
  border-radius: 12px;
  background-color: rgba(0, 0, 0, 0.05);
}

/* 添加空数据提示样式 */
.empty-data-container {
  margin-top: 30px;
}

.empty-data-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.empty-data-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #909399;
  text-align: center;
}

.empty-icon {
  font-size: 60px;
  margin-bottom: 20px;
  color: #DCDFE6;
}

.empty-data-content h3 {
  font-size: 18px;
  font-weight: 500;
  margin: 0 0 10px 0;
}

.empty-text {
  font-size: 14px;
  line-height: 1.5;
  margin: 0;
}
</style> 