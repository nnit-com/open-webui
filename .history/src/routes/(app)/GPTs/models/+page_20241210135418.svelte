<script>
	import { onMount } from 'svelte';
	import { models } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import Models from '$lib/components/Masks/Models.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				models.set(await getModels(localStorage.token));
				models = models.map((model) => ({
    ...model,
    is_showInSidebar: model.is_showInSidebar ?? false, // 保留字段或设置默认值
}));
			})()
		]);
	});
</script>

{#if $models !== null}
	<Models />
{/if}
