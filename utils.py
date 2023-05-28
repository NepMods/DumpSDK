def getUtils():
    return """
#include <iostream>
#include <dlfcn.h>
#include <thread>
#include <string>
#include <cstring>
#include <string>
#include <sstream>
#include <iomanip>

uintptr_t getLib(const char *library) {
        char filename[0xFF] = {
            0
        },
        buffer[1024] = {
            0
        };
        FILE *fp = NULL;
        uintptr_t address = 0;
        sprintf(filename, ("/proc/self/maps"));
        fp = fopen(filename, ("rt"));
        if (fp == NULL) {
            perror(("fopen"));
            goto done;
        }
        while (fgets(buffer, sizeof(buffer), fp)) {
            if (strstr(buffer, library)) {
                address = (uintptr_t) strtoul(buffer, NULL, 16);
                goto done;
            }
        }
        done:
        if (fp) {
            fclose(fp);
        }
        return address;
    }
uintptr_t getAddress(const chat *name, uintptr_t offset) {
    uintptr_t start = getLib(name);
    return start + offset;
}
"""