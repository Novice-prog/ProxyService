<template>
  <v-app class="app-shell">
    <v-app-bar class="topbar" height="72" flat>
      <div class="brand-mark">
        <v-icon icon="mdi-shield-key-outline" size="24" />
      </div>
      <v-app-bar-title class="brand-title">Proxy Access</v-app-bar-title>

      <v-btn
        v-if="isAuthenticated"
        class="cabinet-link"
        prepend-icon="mdi-view-dashboard-outline"
        variant="text"
        color="primary"
        to="/profile"
      >
        Кабинет
      </v-btn>

      <v-spacer />

      <div v-if="!isAuthenticated" class="nav-actions">
        <v-btn prepend-icon="mdi-login" variant="text" to="/login">Вход</v-btn>
        <v-btn prepend-icon="mdi-account-plus-outline" variant="text" to="/register">Регистрация</v-btn>
      </div>
    </v-app-bar>

    <v-main class="main-surface">
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup>
import { isAuthenticated } from './api'
</script>
