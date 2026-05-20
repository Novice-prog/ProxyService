<template>
  <div class="page auth-page">
    <section class="auth-hero">
      <div class="eyebrow">
        <v-icon icon="mdi-shield-crown-outline" size="18" />
        Администрирование
      </div>
      <h1>Вход в панель администратора</h1>
      <p>Управление виртуальными машинами и proxy-узлами сервиса.</p>
    </section>

    <v-card class="auth-card glass-card" variant="flat">
      <v-card-item class="card-heading">
        <template #prepend>
          <div class="card-icon card-icon-accent">
            <v-icon icon="mdi-shield-lock-outline" size="24" />
          </div>
        </template>
        <v-card-title>Аккаунт администратора</v-card-title>
        <v-card-subtitle>Email и пароль из конфигурации сервера</v-card-subtitle>
      </v-card-item>

      <v-card-text>
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
          {{ error }}
        </v-alert>

        <v-form class="auth-form" @submit.prevent="submit">
          <div class="field-block">
            <label class="field-label" for="admin-email">Email</label>
            <v-text-field
              id="admin-email"
              v-model="email"
              type="email"
              autocomplete="username"
              prepend-inner-icon="mdi-email-outline"
              variant="outlined"
              density="comfortable"
              hide-details="auto"
              placeholder="admin@example.com"
              required
            />
          </div>

          <div class="field-block">
            <label class="field-label" for="admin-password">Пароль</label>
            <v-text-field
              id="admin-password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              prepend-inner-icon="mdi-key-outline"
              variant="outlined"
              density="comfortable"
              hide-details="auto"
              placeholder="Введите пароль"
              required
            />
          </div>

          <v-btn
            color="primary"
            type="submit"
            block
            size="large"
            class="primary-action"
            append-icon="mdi-arrow-right"
            :loading="loading"
          >
            Войти
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi } from '../adminApi'

const router = useRouter()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true

  try {
    await adminApi.login({
      email: email.value,
      password: password.value,
    })
    router.push('/admin')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>
