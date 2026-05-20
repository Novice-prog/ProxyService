<template>
  <div class="page admin-page">
    <div class="page-inner">
      <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
        {{ error }}
      </v-alert>

      <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
        {{ success }}
      </v-alert>

      <section class="profile-hero">
        <div>
          <div class="eyebrow">
            <v-icon icon="mdi-server-outline" size="18" />
            Администрирование
          </div>
          <h1>Виртуальные машины</h1>
          <p>Добавляйте proxy-узлы, управляйте доступностью и освобождайте занятые машины.</p>
        </div>
        <v-btn
          variant="tonal"
          prepend-icon="mdi-logout"
          @click="logoutAdmin"
        >
          Выйти
        </v-btn>
      </section>

      <v-card class="dashboard-card mb-4" variant="flat">
          <v-card-item class="card-heading">
            <template #prepend>
              <div class="card-icon">
                <v-icon icon="mdi-plus-circle-outline" size="24" />
              </div>
            </template>
            <v-card-title>Новая виртуальная машина</v-card-title>
            <v-card-subtitle>Создание proxy-узла</v-card-subtitle>
          </v-card-item>

          <v-card-text>
            <v-form @submit.prevent="createVm">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="createForm.name"
                    label="Название"
                    prepend-inner-icon="mdi-label-outline"
                    variant="outlined"
                    required
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="createForm.protocol"
                    :items="protocolOptions"
                    item-title="title"
                    item-value="value"
                    label="Протокол"
                    prepend-inner-icon="mdi-lan"
                    variant="outlined"
                  />
                </v-col>
                <v-col cols="12" md="8">
                  <v-text-field
                    v-model="createForm.host"
                    label="Хост"
                    prepend-inner-icon="mdi-web"
                    variant="outlined"
                    required
                  />
                </v-col>
                <v-col cols="12" md="4">
                  <v-text-field
                    v-model.number="createForm.port"
                    label="Порт"
                    type="number"
                    min="1"
                    max="65535"
                    prepend-inner-icon="mdi-numeric"
                    variant="outlined"
                    required
                  />
                </v-col>
                <v-col cols="12">
                  <v-switch
                    v-model="createForm.is_active"
                    label="Активна"
                    color="primary"
                    hide-details
                  />
                </v-col>
              </v-row>

              <v-btn
                color="primary"
                type="submit"
                size="large"
                prepend-icon="mdi-server-plus"
                :loading="creating"
              >
                Добавить ВМ
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>

        <v-card class="dashboard-card" variant="flat">
          <v-card-item class="card-heading">
            <template #prepend>
              <div class="card-icon">
                <v-icon icon="mdi-server-network-outline" size="24" />
              </div>
            </template>
            <v-card-title>Список машин</v-card-title>
            <v-card-subtitle>{{ vms.length }} записей</v-card-subtitle>
            <template #append>
              <v-btn
                icon="mdi-refresh"
                variant="text"
                :loading="loading"
                @click="loadVms"
              />
            </template>
          </v-card-item>

          <v-card-text>
            <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

            <p v-else-if="vms.length === 0" class="empty-state">
              Виртуальные машины ещё не добавлены.
            </p>

            <div v-else class="vm-list">
              <article v-for="vm in vms" :key="vm.id" class="vm-card">
                <div class="vm-card-head">
                  <div>
                    <h3>{{ vm.name }}</h3>
                    <p>{{ vm.host }}:{{ vm.port }} · {{ vm.protocol }}</p>
                  </div>
                  <div class="vm-chips">
                    <v-chip :color="vm.is_active ? 'success' : 'default'" size="small" variant="flat">
                      {{ vm.is_active ? 'Активна' : 'Выключена' }}
                    </v-chip>
                    <v-chip
                      :color="vm.current_user_id ? 'warning' : 'secondary'"
                      size="small"
                      variant="tonal"
                    >
                      {{ vm.current_user_id ? `Пользователь #${vm.current_user_id}` : 'Свободна' }}
                    </v-chip>
                  </div>
                </div>

                <p v-if="vm.last_used_at" class="vm-meta">
                  Последнее использование: {{ formatDate(vm.last_used_at) }}
                </p>

                <div class="button-row vm-actions">
                  <v-btn
                    size="small"
                    variant="tonal"
                    prepend-icon="mdi-pencil-outline"
                    @click="openEdit(vm)"
                  >
                    Изменить
                  </v-btn>
                  <v-btn
                    size="small"
                    variant="tonal"
                    color="secondary"
                    prepend-icon="mdi-account-off-outline"
                    :disabled="!vm.current_user_id"
                    :loading="releasingId === vm.id"
                    @click="releaseVm(vm.id)"
                  >
                    Освободить
                  </v-btn>
                  <v-btn
                    size="small"
                    variant="tonal"
                    color="error"
                    prepend-icon="mdi-delete-outline"
                    :loading="deletingId === vm.id"
                    @click="deleteVm(vm.id)"
                  >
                    Удалить
                  </v-btn>
                </div>
              </article>
            </div>
          </v-card-text>
        </v-card>

      <v-dialog v-model="editDialog" max-width="560">
        <v-card class="dashboard-card" variant="flat">
          <v-card-item class="card-heading">
            <v-card-title>Редактирование ВМ</v-card-title>
            <v-card-subtitle v-if="editingVm">#{{ editingVm.id }} · {{ editingVm.name }}</v-card-subtitle>
          </v-card-item>

          <v-card-text>
            <v-form @submit.prevent="saveEdit">
              <v-text-field
                v-model="editForm.name"
                label="Название"
                variant="outlined"
                class="mb-2"
              />
              <v-text-field
                v-model="editForm.host"
                label="Хост"
                variant="outlined"
                class="mb-2"
              />
              <v-text-field
                v-model.number="editForm.port"
                label="Порт"
                type="number"
                min="1"
                max="65535"
                variant="outlined"
                class="mb-2"
              />
              <v-select
                v-model="editForm.protocol"
                :items="protocolOptions"
                item-title="title"
                item-value="value"
                label="Протокол"
                variant="outlined"
                class="mb-2"
              />
              <v-switch
                v-model="editForm.is_active"
                label="Активна"
                color="primary"
                hide-details
                class="mb-4"
              />

              <div class="button-row">
                <v-btn variant="text" @click="editDialog = false">Отмена</v-btn>
                <v-btn color="primary" type="submit" :loading="savingEdit">Сохранить</v-btn>
              </div>
            </v-form>
          </v-card-text>
        </v-card>
      </v-dialog>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi } from '../adminApi'

const router = useRouter()

const protocolOptions = [
  { title: 'SOCKS5', value: 'socks5' },
  { title: 'HTTP', value: 'http' },
  { title: 'HTTPS', value: 'https' },
]

const vms = ref([])
const loading = ref(false)
const creating = ref(false)
const savingEdit = ref(false)
const releasingId = ref(null)
const deletingId = ref(null)
const error = ref('')
const success = ref('')
const editDialog = ref(false)
const editingVm = ref(null)

const createForm = reactive({
  name: '',
  host: '',
  port: 1080,
  protocol: 'socks5',
  is_active: true,
})

const editForm = reactive({
  name: '',
  host: '',
  port: 1080,
  protocol: 'socks5',
  is_active: true,
})

onMounted(loadVms)

function logoutAdmin() {
  adminApi.logout()
  router.push('/admin/login')
}

async function loadVms() {
  error.value = ''
  loading.value = true

  try {
    vms.value = await adminApi.listVms()
  } catch (err) {
    if (!err.handled) {
      error.value = err.message
    }
  } finally {
    loading.value = false
  }
}

async function createVm() {
  error.value = ''
  success.value = ''
  creating.value = true

  try {
    await adminApi.createVm({ ...createForm })
    success.value = 'Виртуальная машина добавлена'
    createForm.name = ''
    createForm.host = ''
    createForm.port = 1080
    createForm.protocol = 'socks5'
    createForm.is_active = true
    await loadVms()
  } catch (err) {
    if (!err.handled) {
      error.value = err.message
    }
  } finally {
    creating.value = false
  }
}

function openEdit(vm) {
  editingVm.value = vm
  editForm.name = vm.name
  editForm.host = vm.host
  editForm.port = vm.port
  editForm.protocol = vm.protocol
  editForm.is_active = vm.is_active
  editDialog.value = true
}

async function saveEdit() {
  if (!editingVm.value) {
    return
  }

  error.value = ''
  success.value = ''
  savingEdit.value = true

  try {
    await adminApi.updateVm(editingVm.value.id, { ...editForm })
    success.value = 'Изменения сохранены'
    editDialog.value = false
    await loadVms()
  } catch (err) {
    if (!err.handled) {
      error.value = err.message
    }
  } finally {
    savingEdit.value = false
  }
}

async function releaseVm(vmId) {
  error.value = ''
  success.value = ''
  releasingId.value = vmId

  try {
    await adminApi.releaseVm(vmId)
    success.value = 'ВМ освобождена'
    await loadVms()
  } catch (err) {
    if (!err.handled) {
      error.value = err.message
    }
  } finally {
    releasingId.value = null
  }
}

async function deleteVm(vmId) {
  if (!window.confirm('Удалить виртуальную машину?')) {
    return
  }

  error.value = ''
  success.value = ''
  deletingId.value = vmId

  try {
    await adminApi.deleteVm(vmId)
    success.value = 'ВМ удалена'
    await loadVms()
  } catch (err) {
    if (!err.handled) {
      error.value = err.message
    }
  } finally {
    deletingId.value = null
  }
}

function formatDate(value) {
  if (!value) {
    return '—'
  }

  return new Date(value).toLocaleString('ru-RU')
}
</script>
