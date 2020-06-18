

#include <stdio.h>
#include <string.h>
#include <time.h>

#include <stdlib.h>

int main(void) {

    char    client_time_str[9];
    int     i;
    time_t      client_time;    

    time(&client_time);



    for (client_time_str[0] = i = 0; i < sizeof(client_time); i++) {
        char tmp[3];
        snprintf(tmp, sizeof(tmp), "%02X", (unsigned int)((client_time >> (i * 8)) & 0xFF));
        strcat(client_time_str, tmp);
    }

    //printf("Client time\n");

    printf("%s\n",client_time_str);

    //printf("sizeof time t %u\n", sizeof(time_t));

}