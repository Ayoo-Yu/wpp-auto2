<!-- src/components/Layout.vue -->
<template>
  <el-container class="app-container">
    <!-- 背景容器：内联样式根据开关动态控制动画播放状态 -->
    <div class="background-container">
      <div :style="backgroundStyle"></div>
    </div>

    <!-- 侧边栏 -->
    <el-aside
      :width="isCollapsed ? '64px' : '240px'"
      class="sidebar"
    >
      <!-- 品牌标识 -->
      <div class="brand" @click="toggleCollapse">
        <img
          v-if="!isCollapsed"
          src="@/assets/Hust_logo.png"
          alt="Logo"
          class="brand-logo"
        />
        <el-icon v-else class="collapse-icon">
          <Expand />
        </el-icon>
      </div>

      <!-- 菜单 -->
      <el-menu
        :default-active="activeMenu"
        class="el-menu-vertical"
        :collapse="isCollapsed"
        @select="handleSelect"
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <template #title>首页</template>
        </el-menu-item>

        <el-menu-item index="/modeltrain" v-if="hasPermission('train_models')">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>模型训练</template>
        </el-menu-item>

        <el-menu-item index="/powerpredict" v-if="hasPermission('run_predictions')">
          <el-icon><TrendCharts /></el-icon>
          <template #title>功率预测</template>
        </el-menu-item>

        <el-menu-item index="/autopredict" v-if="hasPermission('run_predictions')">
          <el-icon><Timer /></el-icon>
          <template #title>自动预测</template>
        </el-menu-item>

        <el-menu-item index="/powercompare" v-if="hasPermission('view_all_data')">
          <el-icon><TrendCharts /></el-icon>
          <template #title>功率对比</template>
        </el-menu-item>
        
        <el-menu-item index="/users" v-if="hasPermission('manage_users')">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主要内容区域 -->
    <el-container class="main-container">
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="toggleCollapse">
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
          <h1 class="header-title">华中科技大学风电功率预测平台</h1>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-profile">
              <el-avatar :size="32" class="avatar">{{ userInitial }}</el-avatar>
              <span class="username">{{ userName }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区域 -->
      <el-main class="main-content">
        <router-view></router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
import { ref, computed, provide, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

// 引入 Element Plus 图标
import {
  HomeFilled,
  DataAnalysis,
  Fold,
  Expand,
  TrendCharts,
  Timer,
  User,
} from '@element-plus/icons-vue'

export default {
  name: 'AppLayout',
  components: {
    HomeFilled,
    DataAnalysis,
    Fold,
    Expand,
    TrendCharts,
    Timer,
    User,
  },
  setup() {
    const isCollapsed = ref(false)
    const isAnimatedBackground = ref(true)
    const router = useRouter()
    const route = useRoute()
    
    // 用户信息
    const currentUser = ref(null)

    // 将 isAnimatedBackground 提供给子组件使用
    provide('isAnimatedBackground', isAnimatedBackground)

    // 计算背景内联样式
    const backgroundStyle = computed(() => ({
      position: 'absolute',
      top: '0',
      left: '0',
      width: '100%',
      height: '100%',
      background: 'linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab)',
      backgroundSize: '400% 400%',
      opacity: '1',
      transition: 'opacity 0.5s ease',
      animation: 'gradient 15s ease infinite',
      animationPlayState: isAnimatedBackground.value ? 'running' : 'paused'
    }))

    const activeMenu = computed(() => (route.path === '/' ? '/' : route.path))
    
    // 计算用户名首字母
    const userInitial = computed(() => {
      const userStr = localStorage.getItem('user')
      if (!userStr) return 'U'
      const user = JSON.parse(userStr)
      return user.full_name ? user.full_name.charAt(0).toUpperCase() : 
             user.username.charAt(0).toUpperCase()
    })
    
    // 计算用户显示名称
    const userName = computed(() => {
      const userStr = localStorage.getItem('user')
      if (!userStr) return '用户'
      const user = JSON.parse(userStr)
      return user.full_name || user.username
    })
    
    // 获取当前用户信息
    const fetchCurrentUser = async () => {
      try {
        const userStr = localStorage.getItem('user')
        if (!userStr) {
          router.push('/login')
          return
        }
        
        currentUser.value = JSON.parse(userStr)
      } catch (error) {
        console.error('获取用户信息失败:', error)
        // 如果获取用户信息失败，重定向到登录页
        localStorage.removeItem('user')
        router.push('/login')
      }
    }
    
    // 检查权限
    const hasPermission = (permission) => {
      // 简化权限检查，只要是管理员就有所有权限
      if (!currentUser.value) return false
      
      // 检查用户的权限列表
      if (currentUser.value.permissions) {
        // 处理权限可能是数组或嵌套对象的情况
        let permissions = currentUser.value.permissions;
        
        // 如果权限是对象且有permissions属性
        if (typeof permissions === 'object' && !Array.isArray(permissions) && permissions.permissions) {
          permissions = permissions.permissions;
        }
        
        // 如果权限是数组
        if (Array.isArray(permissions)) {
          // 如果用户权限中包含所需权限，则返回true
          return permissions.includes(permission);
        }
      }
      
      // 向下兼容：系统管理员拥有所有权限
      return currentUser.value.role === '系统管理员'
    }

    const toggleCollapse = () => {
      isCollapsed.value = !isCollapsed.value
    }

    const handleSelect = (index) => {
      router.push(index)
    }
    
    // 处理下拉菜单命令
    const handleCommand = (command) => {
      if (command === 'logout') {
        handleLogout()
      }
    }
    
    // 处理退出登录
    const handleLogout = () => {
      ElMessageBox.confirm(
        '确定要退出登录吗？',
        '提示',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(() => {
        // 清除本地存储的令牌和用户信息
        localStorage.removeItem('user')
        
        // 重定向到登录页
        router.push('/login')
        
        ElMessage.success('已退出登录')
      }).catch(() => {
        // 取消退出
      })
    }
    
    // 生命周期钩子
    onMounted(() => {
      fetchCurrentUser()
    })

    return {
      isCollapsed,
      isAnimatedBackground,
      activeMenu,
      toggleCollapse,
      handleSelect,
      backgroundStyle,
      currentUser,
      userInitial,
      userName,
      handleCommand,
      hasPermission
    }
  },
}
</script>

<style scoped>
/* 主容器 */
.app-container {
  height: 100vh;
  position: relative;
}

/* 对话框样式 */
.dialog-footer {
  text-align: right;
  margin-top: 20px;
}

.custom-form :deep(.el-form-item__content) {
  flex-wrap: nowrap;
  justify-content: flex-start;
}

/* 背景容器 */
.background-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

/* 定义渐变动画 */
@keyframes gradient {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

/* 确保其他内容在背景之上 */
.main-container, .sidebar {
  position: relative;
  z-index: 1;
}

/* 调整主容器背景为透明 */
.main-container {
  background: transparent !important;
}

/* 调整主内容区域背景为透明 */
.main-content {
  background: transparent !important;
  padding: 0;
  overflow-y: auto;
}

/* 侧边栏和顶部导航栏 */
.sidebar {
  background: var(--card-dark);
  border-right: 1px solid var(--border-color);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 1000;
  box-shadow: 4px 0 8px rgba(0, 0, 0, 0.05);
}

.brand {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.brand-logo {
  height: 40px;
  transition: all 0.3s ease;
}

.collapse-icon {
  font-size: 24px;
  color: #ffffff;
}

/* 菜单样式 */
.el-menu-vertical {
  border-right: none;
  background: transparent;
  border: none;
}

.el-menu {
  background: transparent;
  border: none;
}

.el-menu-item {
  color: var(--text-secondary);
  height: 50px;
  margin: 8px 0;
}

.el-menu-item.is-active {
  background: linear-gradient(90deg, rgba(52, 199, 89, 0.1), transparent);
  color: #34C759;
  border-left: 3px solid #34C759;
}

.el-menu-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #ffffff;
}

.el-menu-item .el-icon {
  font-size: 20px;
}

/* 顶部导航栏 */
.header {
  background: var(--card-dark);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-color);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: var(--text-primary);
}

.header-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.003em;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 20px;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.05);
}

.user-profile:hover {
  background: rgba(0, 0, 0, 0.05);
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

/* 响应式 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    height: 100vh;
    left: 0;
    top: 0;
  }

  .header-title {
    font-size: 16px;
  }

  .username {
    display: none;
  }
}
</style>