/* MIT. Exact U632.6.11.2001 ELF transformation; no firmware bytes embedded.
 * All original tables are read from the user's guarded input. See patches/.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <io.h>
#define durable(f) _commit(_fileno(f))
#else
#include <unistd.h>
#define durable(f) fsync(fileno(f))
#endif

#define ORIGINAL_SIZE 598364u
#define PATCHED_SIZE 610748u
static const char original_sha[]="e8ee93b531b4019500ea06f571028330ce3b331f6970b581caaa874295f73a98";
static const char patched_sha[]="c6a4b5bc1e119e4e2c1ff0cc14fb56766448995ca61ba7743f5428e4d30269f5";

/* SHA-256, implemented here from the algorithm in FIPS 180-4. */
static uint32_t rotate(uint32_t x,unsigned n) { return (x>>n)|(x<<(32-n)); }
static void sha256(const unsigned char *input,size_t size,char hex[65])
{
    static const uint32_t k[64]={
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
    uint32_t h[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    size_t total=(size+9+63)&~(size_t)63;
    for(size_t pos=0;pos<total;pos+=64) {
        unsigned char block[64]={0}; uint32_t w[64];
        for(unsigned j=0;j<64;j++) {
            size_t p=pos+j;
            if(p<size) block[j]=input[p];
            else if(p==size) block[j]=128;
            else if(p>=total-8) block[j]=(unsigned char)(((uint64_t)size*8)>>((total-1-p)*8));
        }
        for(unsigned j=0;j<16;j++) w[j]=((uint32_t)block[4*j]<<24)|((uint32_t)block[4*j+1]<<16)|((uint32_t)block[4*j+2]<<8)|block[4*j+3];
        for(unsigned j=16;j<64;j++) {
            uint32_t a=w[j-15],b=w[j-2];
            w[j]=w[j-16]+(rotate(a,7)^rotate(a,18)^(a>>3))+w[j-7]+(rotate(b,17)^rotate(b,19)^(b>>10));
        }
        uint32_t a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],v=h[7];
        for(unsigned j=0;j<64;j++) {
            uint32_t t1=v+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+k[j]+w[j];
            uint32_t t2=(rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c));
            v=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
        }
        h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=v;
    }
    for(unsigned j=0;j<8;j++) sprintf(hex+8*j,"%08x",(unsigned)h[j]);
}
static void fail(const char *s) { fprintf(stderr,"PATCH_REFUSED: %s\n",s); exit(1); }
static uint32_t rd(const unsigned char *p) { return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
static unsigned rd16(const unsigned char *p) { return p[0]|((unsigned)p[1]<<8); }
static void wr(unsigned char *p,uint32_t n) { for(unsigned i=0;i<4;i++) p[i]=(unsigned char)(n>>(8*i)); }
static void wr16(unsigned char *p,unsigned n) { p[0]=(unsigned char)n;p[1]=(unsigned char)(n>>8); }
static uint32_t align4(uint32_t n) { return (n+3)&~3u; }
static uint32_t target(uint32_t word,uint32_t address) { return address+(uint32_t)((int32_t)(word<<1)/2); }
static uint32_t prel(uint32_t address,uint32_t destination) { return (destination-address)&0x7fffffff; }
static void range(uint32_t off,uint32_t size) { if(off>ORIGINAL_SIZE || size>ORIGINAL_SIZE-off) fail("ELF boundary"); }

/* ARM words assembled from our navigation-subtitle.s; 24 + 9 instructions.
 * File offsets and module-relative addresses coincide in the added RX segment.
 */
static const uint32_t code[]={
    0xe3560000,0x112fff1e,0xe59d0058,0xe59001cc,0xe3500000,0x012fff1e,
    0xe5901004,0xe3510005,0x1a00000b,0xe590100c,0xe3510004,0x1a000008,
    0xe5901008,0xe5911000,0xe3062574,0xe3472478,0xe1510002,0x1a000002,
    0xe5900024,0xe3500000,0xe12fff1e,0xe3a00000,0xe3500000,0xe12fff1e,
    0xe3560000,0x159101b8,0x159111bc,0x112fff1e,0xe59101cc,0xe59111d0,
    0xe3500000,0x12800018,0xe12fff1e};

int main(int argc,char **argv)
{
    if(argc==2 && !strcmp(argv[1],"--self-test")) {
        char h[65];sha256((const unsigned char *)"abc",3,h);
        if(strcmp(h,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")) fail("SHA self test");
        puts("SHA256_SELF_TEST_OK");return 0;
    }
    if((argc!=5 && argc!=6) || (argc==6 && strcmp(argv[4],"--compare")) || strcmp(argv[1],"Pocket632") || strcmp(argv[2],"U632.6.11.2001")) fail("usage: patcher Pocket632 U632.6.11.2001 ORIGINAL NEW_FILE | --compare REFERENCE");
    FILE *f=fopen(argv[3],"rb");if(!f) fail("cannot open input");
    unsigned char *out=(unsigned char *)calloc(PATCHED_SIZE+1,1);if(!out) fail("allocation");
    size_t size=fread(out,1,PATCHED_SIZE+1,f);int read_error=ferror(f);fclose(f);
    if(read_error || size!=ORIGINAL_SIZE) fail("original size");
    char hash[65];sha256(out,size,hash);if(strcmp(hash,original_sha)) fail("original SHA-256");
    if(memcmp(out,"\177ELF\1\1\1",7) || rd16(out+18)!=40 || rd(out+28)!=52 || rd16(out+42)!=32 || rd16(out+44)!=6 || rd16(out+46)!=40 || rd16(out+48)!=26) fail("ELF header");
    uint32_t sh=rd(out+32),names_index=rd16(out+50),ex=0;
    range(sh,26*40);if(names_index>=26) fail("string table index");
    for(unsigned i=0;i<26;i++) if(rd(out+sh+i*40+4)==0x70000001) { if(ex) fail("duplicate exidx");ex=sh+i*40; }
    if(!ex) fail("missing exidx");
    uint32_t oldex=rd(out+ex+16),oldaddr=rd(out+ex+12),exsize=rd(out+ex+20);
    uint32_t ns=sh+names_index*40,oldnames=rd(out+ns+16),namesize=rd(out+ns+20);
    range(oldex,exsize);range(oldnames,namesize);if(exsize%8) fail("exidx size");
    uint32_t start=0x93000,first=0x930e0,second=0x93140,newex=0x93164;
    uint32_t names=align4(newex+exsize+24),newsh=align4(names+namesize+12);
    if(newsh+27*40!=PATCHED_SIZE) fail("relocated table boundary");
    memcpy(out+start,out+52,6*32);
    for(unsigned i=0;i<6;i++) {
        unsigned char *p=out+start+i*32;
        if(rd(p)==0x70000001) { wr(p+4,newex);wr(p+8,newex);wr(p+12,newex);wr(p+16,exsize+24);wr(p+20,exsize+24); }
    }
    uint32_t ph[]={1,start,start,start,PATCHED_SIZE-start,PATCHED_SIZE-start,5,4096};
    for(unsigned i=0;i<8;i++) wr(out+start+6*32+i*4,ph[i]);
    for(unsigned i=0;i<sizeof(code)/sizeof(code[0]);i++) wr(out+first+i*4,code[i]);
    for(uint32_t i=0;i<exsize;i+=8) {
        uint32_t fn=rd(out+oldex+i),word=rd(out+oldex+i+4);
        wr(out+newex+i,prel(newex+i,target(fn,oldaddr+i)));
        wr(out+newex+i+4,(word==1 || (word&0x80000000))?word:prel(newex+i+4,target(word,oldaddr+i+4)));
    }
    uint32_t destinations[]={first,second,first+sizeof(code)};
    for(unsigned i=0;i<3;i++) { wr(out+newex+exsize+i*8,prel(newex+exsize+i*8,destinations[i]));wr(out+newex+exsize+i*8+4,i<2?0x80b0b0b0:1); }
    memcpy(out+names,out+oldnames,namesize);memcpy(out+names+namesize,".opds_patch\0",12);
    memcpy(out+newsh,out+sh,26*40);
    uint32_t movedex=newsh+(ex-sh);
    wr(out+movedex+12,newex);wr(out+movedex+16,newex);wr(out+movedex+20,exsize+24);
    wr(out+newsh+names_index*40+16,names);wr(out+newsh+names_index*40+20,namesize+12);
    uint32_t section[]={namesize,1,6,first,first,sizeof(code),0,0,4,0};
    for(unsigned i=0;i<10;i++) wr(out+newsh+26*40+i*4,section[i]);
    if(rd(out+0x3d41c)!=0xe3560000 || rd(out+0x3d558)!=0xe59101b8 || rd(out+0x3d55c)!=0xe59111bc) fail("hook bytes");
    wr(out+28,start);wr(out+32,newsh);wr16(out+44,7);wr16(out+48,27);
    wr(out+0x3d41c,0xeb000000|((first-0x3d41c-8)/4));
    wr(out+0x3d558,0xeb000000|((second-0x3d558-8)/4));wr(out+0x3d55c,0xe320f000);
    sha256(out,PATCHED_SIZE,hash);if(strcmp(hash,patched_sha)) fail("result differs from tested universal-v8");
    if(argc==6) {
        f=fopen(argv[5],"rb");if(!f) fail("cannot open private reference");
        unsigned char buffer[4096];size_t pos=0,n;
        while((n=fread(buffer,1,sizeof(buffer),f))>0) {
            if(n>PATCHED_SIZE-pos || memcmp(out+pos,buffer,n)) fail("private reference byte mismatch");
            pos+=n;
        }
        if(ferror(f) || pos!=PATCHED_SIZE) fail("private reference size");
        fclose(f);free(out);puts("REFERENCE_EXACT_BYTE_MATCH (in memory, no firmware output written)");return 0;
    }
    f=fopen(argv[4],"wbx");if(!f) fail("output must be a new file (no overwrite)");
    int error=fwrite(out,1,PATCHED_SIZE,f)!=PATCHED_SIZE;
    if(fflush(f) || durable(f)) error=1;
    if(fclose(f)) error=1;
    free(out);
    if(error) { remove(argv[4]);fail("output write/sync failed"); }
    printf("PATCH_VERIFIED: %s\n",hash);return 0;
}
