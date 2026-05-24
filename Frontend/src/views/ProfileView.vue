<template>
  <div class="page profile-page">
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
            <v-icon icon="mdi-view-dashboard-outline" size="18" />
            Личный кабинет
          </div>
          <h1>Управление доступом</h1>
          <p>Контролируйте статус аккаунта, сроки ключа и безопасность профиля.</p>
        </div>
        <v-chip
          v-if="user"
          :color="user.is_active ? 'success' : 'warning'"
          variant="flat"
          size="large"
          class="status-chip"
        >
          <v-icon start :icon="user.is_active ? 'mdi-check-circle-outline' : 'mdi-alert-circle-outline'" />
          {{ user.is_active ? 'Аккаунт активен' : 'Нужна активация' }}
        </v-chip>
      </section>

      <v-row class="content-grid">
        <v-col cols="12" lg="7">
          <v-card class="dashboard-card account-card" variant="flat">
            <v-card-item class="card-heading">
              <template #prepend>
                <div class="card-icon">
                  <v-icon icon="mdi-account-shield-outline" size="24" />
                </div>
              </template>
              <v-card-title>Профиль</v-card-title>
              <v-card-subtitle>Основные данные аккаунта</v-card-subtitle>
            </v-card-item>

            <v-card-text v-if="user">
              <div class="info-grid">
                <div class="info-tile wide">
                  <v-icon icon="mdi-email-outline" />
                  <span>Email</span>
                  <strong>{{ user.email }}</strong>
                </div>
                <div class="info-tile wide">
                  <v-icon :icon="user.is_active ? 'mdi-check-decagram-outline' : 'mdi-clock-alert-outline'" />
                  <span>Статус</span>
                  <strong>{{ user.is_active ? 'Активен' : 'Не активен' }}</strong>
                </div>
                <div class="info-tile wide">
                  <v-icon icon="mdi-calendar-clock-outline" />
                  <span>Истекает</span>
                  <strong>{{ formatDate(user.activation_key_expires) }}</strong>
                </div>
                <div class="info-tile wide key-tile">
                  <v-icon icon="mdi-email-check-outline" />
                  <span>Ключ активации</span>
                  <strong>
                    {{ user.has_pending_activation_key
                        ? 'Отправлен на email'
                        : 'Не запрошен или уже использован' }}
                  </strong>
                </div>
              </div>

              <div class="button-row">
                <v-btn
                  color="primary"
                  size="large"
                  prepend-icon="mdi-refresh"
                  :loading="refreshingKey"
                  @click="refreshKey"
                >
                  Обновить ключ
                </v-btn>

                <v-btn
                  variant="tonal"
                  size="large"
                  prepend-icon="mdi-logout"
                  @click="logout"
                >
                  Выйти
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" lg="5">
          <v-card class="dashboard-card" variant="flat">
            <v-card-item class="card-heading">
              <template #prepend>
                <div class="card-icon card-icon-accent">
                  <v-icon icon="mdi-lock-reset" size="24" />
                </div>
              </template>
              <v-card-title>Смена пароля</v-card-title>
              <v-card-subtitle>Обновите учетные данные</v-card-subtitle>
            </v-card-item>

            <v-card-text>
              <v-form class="auth-form" @submit.prevent="changePassword">
                <div class="field-block">
                  <label class="field-label" for="old-password">Старый пароль</label>
                  <v-text-field
                    id="old-password"
                    v-model="oldPassword"
                    class="app-field"
                    type="password"
                    autocomplete="current-password"
                    prepend-inner-icon="mdi-lock-outline"
                    variant="outlined"
                    density="comfortable"
                    hide-details="auto"
                    placeholder="Текущий пароль"
                  />
                </div>

                <div class="field-block">
                  <label class="field-label" for="new-password">Новый пароль</label>
                  <v-text-field
                    id="new-password"
                    v-model="newPassword"
                    class="app-field"
                    type="password"
                    autocomplete="new-password"
                    prepend-inner-icon="mdi-lock-plus-outline"
                    variant="outlined"
                    density="comfortable"
                    hide-details="auto"
                    placeholder="Новый пароль"
                  />
                </div>

                <div class="field-block">
                  <label class="field-label" for="new-password-confirm">Повторите новый пароль</label>
                  <v-text-field
                    id="new-password-confirm"
                    v-model="newPasswordConfirm"
                    class="app-field"
                    type="password"
                    autocomplete="new-password"
                    prepend-inner-icon="mdi-lock-check-outline"
                    variant="outlined"
                    density="comfortable"
                    hide-details="auto"
                    placeholder="Повторите пароль"
                  />
                </div>

                <v-btn
                  color="primary"
                  type="submit"
                  size="large"
                  block
                  append-icon="mdi-check"
                  :loading="changingPassword"
                >
                  Сменить пароль
                </v-btn>
              </v-form>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()

const user = ref(null)
const error = ref('')
const success = ref('')
const refreshingKey = ref(false)
const changingPassword = ref(false)

const oldPassword = ref('')
const newPassword = ref('')
const newPasswordConfirm = ref('')

onMounted(loadProfile)

async function loadProfile() {
  error.value = ''

  try {
    user.value = await api.profile()
  } catch (err) {
    if (!err.handled) {
      error.value = err.message
    }
  }
}

async function refreshKey() {
  error.value = ''
  success.value = 'Новый ключ отправлен на ваш email. Старый ключ больше не действителен.'
  refreshingKey.value = true

  try {
    await api.refreshKey()
    success.value = 'Новый ключ отправлен на почту'
    await loadProfile()
  } catch (err) {
    if (!err.handled) {
      error.value = err.message
    }
  } finally {
    refreshingKey.value = false
  }
}

async function changePassword() {
  error.value = ''
  success.value = ''
  changingPassword.value = true

  try {
    await api.changePassword({
      old_password: oldPassword.value,
      new_password: newPassword.value,
      new_password_confirm: newPasswordConfirm.value,
    })
    success.value = 'Пароль успешно изменён'
    oldPassword.value = ''
    newPassword.value = ''
    newPasswordConfirm.value = ''
  } catch (err) {
    if (!err.handled) {
      error.value = err.message
    }
  } finally {
    changingPassword.value = false
  }
}

function logout() {
  api.logout()
  router.push('/login')
}

function formatDate(value) {
  if (!value) {
    return 'Нет даты'
  }

  return new Date(value).toLocaleString('ru-RU')
}
</script>
