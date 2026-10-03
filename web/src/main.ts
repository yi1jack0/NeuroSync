import './app.css';
import { mount } from 'svelte';
import App from './ui/App.svelte';
import { app } from './state/app.svelte';

mount(App, { target: document.getElementById('app')! });
void app.init();
