<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		if ($user?.role !== 'admin') {
			if ($user?.permissions?.Masks?.models) {
				goto('/Masks/models');
			} else {
				goto('/');
			}
		} else {
			goto('/Masks/models');
		}
	});
</script>
