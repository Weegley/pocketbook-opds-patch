.syntax unified
.arm
.text
.global first_helper
first_helper:

cmp r6, #0
bxne lr
ldr r0, [sp, #0x58]
ldr r0, [r0, #0x1cc]
cmp r0, #0
bxeq lr
ldr r1, [r0, #4]
cmp r1, #5
bne no_subtitle
ldr r1, [r0, #0xc]
cmp r1, #4
bne no_subtitle
ldr r1, [r0, #8]
ldr r1, [r1]
movw r2, #0x6574
movt r2, #0x7478
cmp r1, r2
bne no_subtitle
ldr r0, [r0, #0x24]
cmp r0, #0
bx lr
no_subtitle:
mov r0, #0
cmp r0, #0
bx lr

load_subtitle:

cmp r6, #0
ldrne r0, [r1, #0x1b8]
ldrne r1, [r1, #0x1bc]
bxne lr
ldr r0, [r1, #0x1cc]
ldr r1, [r1, #0x1d0]
cmp r0, #0
addne r0, r0, #0x18
bx lr
