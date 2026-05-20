<template>
  <div class="page auth-page">
    <section class="auth-hero">
      <div class="eyebrow">
        <v-icon icon="mdi-lock-check-outline" size="18" />
        Безопасный доступ
      </div>
      <h1>Войдите в панель управления proxy-доступом</h1>
      <p>Проверяйте статус аккаунта, обновляйте ключи активации и управляйте профилем из одного спокойного интерфейса.</p>
    </section>

    <v-card class="auth-card glass-card" variant="flat">
      <v-card-item class="card-heading">
        <template #prepend>
          <div class="card-icon">
            <v-icon icon="mdi-login" size="24" />
          </div>
        </template>
        <v-card-title>Вход</v-card-title>
        <v-card-subtitle>Откройте личный кабинет</v-card-subtitle>
      </v-card-item>

      <v-card-text>
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
          {{ error }}
        </v-alert>

        <v-form class="auth-form" @submit.prevent="submit">
          <div class="field-block">
            <label class="field-label" for="login-email">Email</label>
            <v-text-field
              id="login-email"
              v-model="email"
              type="email"
              autocomplete="email"
              prepend-inner-icon="mdi-email-outline"
              variant="outlined"
              density="comfortable"
              hide-details="auto"
              placeholder="you@example.com"
              required
            />
          </div>

          <div class="field-block">
            <label class="field-label" for="login-password">Пароль</label>
            <v-text-field
              id="login-password"
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
import { api } from '../api'

const router = useRouter()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true

  try {
    await api.login({
      email: email.value,
      password: password.value,
    })
    router.push('/profile')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>
