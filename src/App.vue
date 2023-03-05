<template>
  <div id="app">
    <ThreePage />
  </div>
</template>

<script>
import ThreePage from './components/ThreePage.vue'

export default {
  name: 'App',
  components: {
    ThreePage
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 0px;
}
</style>
