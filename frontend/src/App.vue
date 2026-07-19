<template>
  <router-view />
  <DevReplayBar />
  <OpenSourceNotice />
</template>

<script setup>
import DevReplayBar from './components/DevReplayBar.vue'
import OpenSourceNotice from './components/OpenSourceNotice.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  min-height: 100vh;
  font-family: var(--mf-font);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--mf-ink);
  background: var(--mf-canvas);
}
</style>
