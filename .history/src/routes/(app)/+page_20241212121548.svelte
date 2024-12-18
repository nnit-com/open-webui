<script lang="ts">
	import Chat from '$lib/components/chat/Chat.svelte';
	import Help from '$lib/components/layout/Help.svelte';
	import { onMount } from 'svelte';

	onMount(() => {
		
			goto('/Masks/models');
	
	});
</script>

<Help />

<Chat />
