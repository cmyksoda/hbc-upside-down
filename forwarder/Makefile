ifeq ($(strip $(DEVKITPPC)),)
$(error "Please set DEVKITPPC in your environment. export DEVKITPPC=<path to>devkitPPC")
endif

include $(DEVKITPPC)/wii_rules

DEPSDIR  := $(CURDIR)
LD       := $(CC)
CFLAGS   := -O2 -Wall $(MACHDEP) -I$(LIBOGC_INC)
LDFLAGS  := $(MACHDEP) -Wl,-Map,forwarder.map
LIBPATHS := -L$(LIBOGC_LIB)
LIBS     := -logc

forwarder.dol: forwarder.elf
forwarder.elf: source/main.o

clean:
	rm -f source/*.o source/*.d forwarder.elf forwarder.dol forwarder.map
