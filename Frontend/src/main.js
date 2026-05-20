import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import {
  VAlert,
  VApp,
  VAppBar,
  VAppBarTitle,
  VBtn,
  VCard,
  VCardItem,
  VCardSubtitle,
  VCardText,
  VCardTitle,
  VChip,
  VCol,
  VDialog,
  VForm,
  VIcon,
  VMain,
  VProgressLinear,
  VRow,
  VSelect,
  VSpacer,
  VSwitch,
  VTextField,
} from 'vuetify/components'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import './styles.css'

import App from './App.vue'
import LoginView from './views/LoginView.vue'
import ProfileView from './views/ProfileView.vue'
import RegisterView from './views/RegisterView.vue'
import AdminVmsView from './views/AdminVmsView.vue'
import AdminLoginView from './views/AdminLoginView.vue'
import { isAuthenticated, setRouter } from './api'
import { isAdminAuthenticated, setAdminRouter } from './adminApi'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/register', component: RegisterView, meta: { guestOnly: true } },
  { path: '/login', component: LoginView, meta: { guestOnly: true } },
  { path: '/profile', component: ProfileView, meta: { requiresAuth: true } },
  {
    path: '/admin/login',
    component: AdminLoginView,
    beforeEnter() {
      if (isAdminAuthenticated.value) {
        return '/admin'
      }
    },
  },
  {
    path: '/admin',
    component: AdminVmsView,
    beforeEnter() {
      if (!isAdminAuthenticated.value) {
        return '/admin/login'
      }
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return '/login'
  }

  if (to.meta.guestOnly && isAuthenticated.value) {
    return '/profile'
  }
})

setRouter(router)
setAdminRouter(router)

const vuetify = createVuetify({
  components: {
    VAlert,
    VApp,
    VAppBar,
    VAppBarTitle,
    VBtn,
    VCard,
    VCardItem,
    VCardSubtitle,
    VCardText,
    VCardTitle,
    VChip,
    VCol,
    VDialog,
    VForm,
    VIcon,
    VMain,
    VProgressLinear,
    VRow,
    VSelect,
    VSpacer,
    VSwitch,
    VTextField,
  },
  theme: {
    defaultTheme: 'serviceTheme',
    themes: {
      serviceTheme: {
        dark: false,
        colors: {
          primary: '#2563eb',
          secondary: '#0f766e',
          accent: '#f97316',
          surface: '#ffffff',
          background: '#f7f8fb',
          error: '#dc2626',
          success: '#16a34a',
        },
      },
    },
  },
})

createApp(App).use(router).use(vuetify).mount('#app')
