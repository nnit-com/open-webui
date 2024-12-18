<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { Confetti } from 'svelte-confetti';

	import { WEBUI_NAME, config, settings } from '$lib/stores';

	import { WEBUI_VERSION ,WEBUI_BASE_URL} from '$lib/constants';
	import { getChangelog } from '$lib/apis';

	import Modal from './common/Modal.svelte';
	import { updateUserSettings } from '$lib/apis/users';

	const i18n = getContext('i18n');

	export let show = false;

	let changelog = null;

	onMount(async () => {
		const res = await getChangelog();
		changelog = res;
	});
</script>

<Modal bind:show size="lg">
	<div class="px-5 pt-4 dark:text-gray-300 text-gray-700">
		<div class="flex justify-between items-start">
			<div class="text-xl font-semibold">
				欢迎使用 NNIT ChatGPT
			</div>
			<button
				class="self-center"
				on:click={() => {
					localStorage.version = $config.version;
					show = false; // 关闭提示
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
	
		<div class="mt-4 text-sm">
			<p class="font-medium mb-2">在您访问之前请确认并同意以下注意事项：</p>
			<ol class="list-decimal list-inside space-y-2">
				<li>
					<strong>确保使用目的与工作相关：</strong>
					使用 ChatGPT 解决工作中的具体问题，如编写代码、生成报告、优化工作流程等。
					避免在工作时间内使用 ChatGPT 进行与工作无关的娱乐或私人对话。
				</li>
				<li>
					<strong>遵守法律法规：</strong>
					使用 ChatGPT 时，确保内容符合当地法律法规和公司政策。
					避免生成可能违法或违规的内容，包括侵犯版权的材料。
				</li>
				<li>
					<strong>保护公司内部数据：</strong>
					不要输入或讨论任何敏感或保密的公司信息。
					使用 ChatGPT 处理公司数据前，确保数据已去标识化，无法追溯到个人或公司。
				</li>
				<li>
					<strong>避免讨论敏感话题：</strong>
					避免使用 ChatGPT 讨论可能引起争议的政治、宗教话题。
					不应使用 ChatGPT 讨论任何种族、性别歧视或其他敏感的社会问题。
				</li>
				<li>
					<strong>监督与反馈：</strong>
					所有会话都会保留会话日志，公司会不定时审核员工使用 ChatGPT 的情况，确保使用符合本指南。
					欢迎大家对使用 ChatGPT 的经验提供反馈，以改善未来的使用指导和政策。
				</li>
				<li>
					<strong>个人责任：</strong>
					员工需对其在 ChatGPT 上的行为和生成的内容负责。
					任何违反指南的行为可能会受到相应的纪律处分。
				</li>
			</ol>
		</div>
	
		<!-- <div class="flex justify-between items-start">
			<div class="text-xl font-semibold">
				{$i18n.t('What’s New in')}
				{$WEBUI_NAME}
				<Confetti x={[-1, -0.25]} y={[0, 0.5]} />
			</div>
			<button
				class="self-center"
				on:click={() => {
					localStorage.version = $config.version;
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<div class="flex items-center mt-1">
			<div class="text-sm dark:text-gray-200">{$i18n.t('Release Notes')}</div>
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700" />
			<div class="text-sm dark:text-gray-200">
				v{WEBUI_VERSION}
			</div>
		</div>
	</div>

	<div class=" w-full p-4 px-5 text-gray-700 dark:text-gray-100">
		<div class=" overflow-y-scroll max-h-96 scrollbar-hidden">
			<div class="mb-3">
				{#if changelog}
					{#each Object.keys(changelog) as version}
						<div class=" mb-3 pr-2">
							<div class="font-semibold text-xl mb-1 dark:text-white">
								v{version} - {changelog[version].date}
							</div>

							<hr class=" dark:border-gray-800 my-2" />

							{#each Object.keys(changelog[version]).filter((section) => section !== 'date') as section}
								<div class="">
									<div
										class="font-semibold uppercase text-xs {section === 'added'
											? 'text-white bg-blue-600'
											: section === 'fixed'
												? 'text-white bg-green-600'
												: section === 'changed'
													? 'text-white bg-yellow-600'
													: section === 'removed'
														? 'text-white bg-red-600'
														: ''}  w-fit px-3 rounded-full my-2.5"
									>
										{section}
									</div>

									<div class="my-2.5 px-1.5">
										{#each Object.keys(changelog[version][section]) as item}
											<div class="text-sm mb-2">
												<div class="font-semibold uppercase">
													{changelog[version][section][item].title}
												</div>
												<div class="mb-2 mt-1">{changelog[version][section][item].content}</div>
											</div>
										{/each}
									</div>
								</div>
							{/each}
						</div>
					{/each}
				{/if}
			</div>
		</div> -->
		<div class="flex justify-end pt-3 text-sm font-medium">
			<button
			on:click={() => {
				// 清除本地存储中的 token
				delete localStorage.token;
				window.location.href = `${WEBUI_BASE_URL}/auth`;
				}}
			class="px-3.5 py-1.5 text-sm font-medium bg-red-600 hover:bg-red-700 text-white dark:bg-red-400 dark:text-black dark:hover:bg-red-500 transition rounded-full"
		>
			<span class="relative">{$i18n.t("Cancel and Logout")}</span>
		</button>
			<button
				on:click={async () => {
					localStorage.version = $config.version;
					await settings.set({ ...$settings, ...{ version: $config.version } });
					await updateUserSettings(localStorage.token, { ui: $settings });
					show = false;
				}}
				class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			>
				<span class="relative">{$i18n.t("Okay, Let's Go!")}</span>
			</button>
		</div>
	</div>
</Modal>
