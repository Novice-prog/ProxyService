<template>
  <div class="page auth-page">
    <section class="auth-hero">
      <div class="eyebrow">
        <v-icon icon="mdi-email-fast-outline" size="18" />
        Быстрый старт
      </div>
      <h1>Создайте аккаунт и получите ключ активации</h1>
      <p>После регистрации система отправит ключ на email, чтобы вы могли подключить доступ без лишних шагов.</p>
    </section>

    <v-card class="auth-card glass-card" variant="flat">
      <v-card-item class="card-heading">
        <template #prepend>
          <div class="card-icon">
            <v-icon icon="mdi-account-plus-outline" size="24" />
          </div>
        </template>
        <v-card-title>Регистрация</v-card-title>
        <v-card-subtitle>Ключ активации придёт на почту</v-card-subtitle>
      </v-card-item>

      <v-card-text>
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
          {{ error }}
        </v-alert>

        <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
          {{ success }}
        </v-alert>

        <v-form v-if="!success" class="auth-form" @submit.prevent="submit">
          <div class="field-block">
            <label class="field-label" for="register-email">Email</label>
            <v-text-field
              id="register-email"
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
            <label class="field-label" for="register-password">Пароль</label>
            <v-text-field
              id="register-password"
              v-model="password"
              type="password"
              autocomplete="new-password"
              prepend-inner-icon="mdi-key-outline"
              variant="outlined"
              density="comfortable"
              hide-details="auto"
              placeholder="Минимум 8 символов"
              required
            />
          </div>

          <div class="field-block">
            <label class="field-label" for="register-password-confirm">Повторите пароль</label>
            <v-text-field
              id="register-password-confirm"
              v-model="passwordConfirm"
              type="password"
              autocomplete="new-password"
              prepend-inner-icon="mdi-lock-outline"
              variant="outlined"
              density="comfortable"
              hide-details="auto"
              placeholder="Повторите пароль"
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
            Зарегистрироваться
          </v-btn>
        </v-form>

        <v-btn
          v-if="success"
          color="primary"
          block
          size="large"
          class="primary-action"
          append-icon="mdi-login"
          @click="goToLogin"
        >
          Перейти ко входу
        </v-btn>
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
const passwordConfirm = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

async function submit() {
  error.value = ''
  success.value = ''
  loading.value = true

  try {
    await api.register({
      email: email.value,
      password: password.value,
      password_confirm: passwordConfirm.value,
    })
    success.value = 'Письмо с ключом отправлено на почту'
    email.value = ''
    password.value = ''
    passwordConfirm.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function goToLogin() {
  router.push('/login')
}
</script>
