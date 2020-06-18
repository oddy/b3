
#include <stdio.h>

int main()
{
    double x = 1e-200;
    double y = 1e-200 * x;
    printf("Reciprocal of +0: %g\n", 1/y);
    y = -1e-200*x;
    printf("Reciprocal of -0: %g\n", 1/y);
}
