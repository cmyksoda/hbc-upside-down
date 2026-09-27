#include <gccore.h>
#include <ogc/es.h>
#include <ogc/wiilaunch.h>

// Every title ID the Homebrew Channel has shipped under, newest first.
static const u32 hbc_ids[] = {
	0x4F484243, // OHBC (1.1.4+)
	0x4C554C5A, // LULZ (1.0.8 - 1.1.3)
	0x4A4F4449, // JODI
	0x48415858, // HAXX
	0xAF1BF516, // 1.0 betas
};

static bool installed(u64 tid)
{
	u32 size, views;
	return ES_GetStoredTMDSize(tid, &size) >= 0
		&& ES_GetNumTicketViews(tid, &views) >= 0 && views > 0;
}

int main(void)
{
	VIDEO_Init();
	WII_Initialize();

	for (int i = 0; i < sizeof(hbc_ids) / sizeof(hbc_ids[0]); i++) {
		u64 tid = 0x0001000100000000ULL | hbc_ids[i];
		if (installed(tid))
			WII_LaunchTitle(tid);
	}

	// No HBC found, or the launch failed.
	WII_ReturnToMenu();
	return 0;
}
