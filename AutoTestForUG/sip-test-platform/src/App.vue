<template>
  <div class="common-layout">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <h1>SIP 自动化测试平台</h1>
          <div class="nav-menu">
            <el-menu
              :default-active="$route.path"
              mode="horizontal"
              router
              background-color="#545c64"
              text-color="#fff"
              active-text-color="#ffd04b"
            >
              <el-menu-item index="/">仪表盘</el-menu-item>
              <el-menu-item index="/suites">测试套件</el-menu-item>
              <el-menu-item index="/scenarios">测试场景</el-menu-item>
              <el-menu-item index="/test-cases">测试用例</el-menu-item>
              <el-menu-item index="/executions">执行监控</el-menu-item>
              <el-menu-item index="/reports">测试报告</el-menu-item>
            </el-menu>
          </div>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
      
      <el-footer class="footer">
        <div class="footer-content">
          SIP 自动化测试平台 &copy; {{ new Date().getFullYear() }}
        </div>
      </el-footer>
    </el-container>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style scoped>
.common-layout {
  min-height: 100vh;
}

.header {
  padding: 0;
  background-color: #545c64;
  box-shadow: 0 2px 4px rgba(0,0,0,.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  height: 60px;
  color: white;
}

.header-content h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: bold;
}

.nav-menu {
  flex-grow: 1;
  margin-left: 20px;
}

.main-content {
  padding: 20px;
  background-color: #f5f5f5;
}

.footer {
  background-color: #545c64;
  color: white;
  text-align: center;
  padding: 10px 0;
  margin-top: auto;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
}
</style>