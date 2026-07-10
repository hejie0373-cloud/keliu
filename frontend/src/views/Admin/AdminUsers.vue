<script setup lang="ts">
import { ref, onMounted } from 'vue'
import http from '@/api/http'

const users = ref<any[]>([])
const loading = ref(false)

onMounted(() => loadUsers())

async function loadUsers() {
  loading.value = true
  const { data } = await http.get('/admin/users')
  users.value = (data as any).items || []
  loading.value = false
}

async function toggleUser(uid: string) {
  await http.put(`/admin/users/${uid}/toggle`)
  loadUsers()
}
</script>

<template>
  <div class="admin-route page">
    <header class="hero" v-reveal>
      <h1>用户管理</h1>
      <p>查看平台账号、角色分配和启用状态。</p>
    </header>

    <div class="table-card" v-reveal>
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="email" label="邮箱" min-width="160">
          <template #default="{ row }">{{ row.email || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="r in row.roles" :key="r" size="small" class="role-tag"
              :type="r === 'super_admin' ? 'danger' : r === 'store_owner' ? 'primary' : 'info'">
              {{ r === 'super_admin' ? '管理员' : r === 'store_owner' ? '店主' : r === 'staff' ? '店员' : r }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.isActive ? 'success' : 'danger'" size="small">{{ row.isActive ? '正常' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" :type="row.isActive ? 'danger' : 'success'" @click="toggleUser(row.id)">
              {{ row.isActive ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.page {
  padding: 16px 24px 40px;
}

.hero {
  margin-bottom: 16px;
}

.hero h1 {
  margin: 0;
  color: var(--admin-text);
  font-size: 1.35rem;
  font-weight: 700;
}

.hero p {
  margin: 4px 0 0;
  color: var(--admin-text-secondary);
  font-size: 0.85rem;
}

.table-card {
  overflow: hidden;
  border: 1px solid var(--admin-border);
  border-radius: 8px;
  background: var(--admin-surface);
}

.role-tag {
  margin-right: 4px;
}
</style>
