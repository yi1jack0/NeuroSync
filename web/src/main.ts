import './app.css';
import { mount } from 'svelte';
import App from './ui/App.svelte';
import { app } from './state/app.svelte';
import { setupOffline } from './lib/offline';

mount(App, { target: document.getElementById('app')! });
void app.init();
setupOffline((ready) => (app.offlineReady = ready));
