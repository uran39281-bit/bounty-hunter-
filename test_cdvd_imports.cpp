// CDVDFSV regression: real filesystem lookup, shared buffer and sector bytes.
#include "emulator/core/iop_cpu.h"
#include "emulator/core/iop_kernel.h"
#include "emulator/core/iop_memory.h"
#include "emulator/imports/iop_cdvd.h"
#include "ps2x/iop/iop_host.h"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <array>
using namespace ps2x::iop;
using namespace ps2x::iop::detail;
void require(bool ok,const char*msg){if(!ok)throw std::runtime_error(msg);}
class FileHost final:public IopHost {
public:
 explicit FileHost(std::filesystem::path p):root(std::move(p)){}
 bool readGuest(uint32_t,void*,size_t)const override{return false;}
 bool writeGuest(uint32_t,const void*,size_t)override{return false;}
 bool zeroGuest(uint32_t,size_t)override{return false;}
 bool normalizeGuestAddress(uint32_t,uint32_t&)const override{return false;}
 uint32_t allocateIopHandle(IopHandleKind)override{return 1;}
 uint32_t allocateGuest(uint32_t,uint32_t)override{return 0;}
 void freeGuest(uint32_t)override{}
 void audioCommand(uint32_t,uint32_t,GuestBuffer,GuestBuffer)override{}
 std::string hostPath(HostPathKind k)const override{return k==HostPathKind::CdRoot?root.string():std::string{};}
 std::string translateGuestPath(std::string_view p)const override{return std::string(p);}
 uint64_t openHostFile(std::string_view path)override{
  auto stream=std::make_unique<std::ifstream>(std::string(path),std::ios::binary);
  if(!*stream)return 0;const auto id=next++;files[id]=std::move(stream);return id;
 }
 bool hostFileSize(uint64_t id,uint64_t&size)const override{
  const auto it=files.find(id);if(it==files.end())return false;
  auto&s=*it->second;s.clear();s.seekg(0,std::ios::end);size=s.tellg();return true;
 }
 bool readHostFile(uint64_t id,uint64_t off,void*dest,size_t size,size_t&count)override{
  const auto it=files.find(id);if(it==files.end())return false;
  auto&s=*it->second;s.clear();s.seekg(off);s.read(static_cast<char*>(dest),size);count=s.gcount();return true;
 }
 void closeHostFile(uint64_t id)override{files.erase(id);}
 int32_t memoryCard(const MemoryCardRequest&)override{return 0;}
 bool hasGuestFunction(uint32_t)const override{return false;}
 bool invokeGuestFunction(uint64_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t*)override{return false;}
 void log(LogLevel,std::string_view)override{}
private:
 std::filesystem::path root;uint64_t next=1;
 std::map<uint64_t,std::unique_ptr<std::ifstream>>files;
};
int main(int argc,char**argv){
 if(argc!=2)return 2;
 const std::filesystem::path root=argv[1];std::filesystem::create_directories(root/"DATA");
 std::ofstream(root/"DATA/TEST.BIN",std::ios::binary)<<"ABCD";
 FileHost host(root);IopMemory memory;IopKernel kernel(memory);kernel.reset();IopCdvd cdvd(host,memory,kernel);cdvd.reset();
 IopCpuState cpu{};unsetenv("PS2X_CDVD_COMPAT");
 require(!cdvd.dispatchImport(47,cpu)&&!cdvd.dispatchImport(84,cpu),"opt-out baseline changed");
 setenv("PS2X_CDVD_COMPAT","1",1);
 require(cdvd.dispatchImport(47,cpu),"FSV buffer import not handled");const auto buffer=cpu.gpr[2];
 require(buffer && (buffer&63u)==0,"FSV buffer not allocated/aligned");
 require(memory.allocationContaining(buffer+42127u).has_value(),"buffer tail not allocated");
 memory.write8(buffer+42127u,0x5a);require(memory.read8(buffer+42127u)==0x5a,"buffer tail not writable");
 cdvd.dispatchImport(47,cpu);require(cpu.gpr[2]==buffer,"shared buffer not stable");
 const char path[]="cdrom0:\\data\\test.bin;1";memory.writeRam(0x2480,path,sizeof(path));
 cpu.gpr[4]=0x2400;cpu.gpr[5]=0x2480;cpu.gpr[6]=0;
 require(cdvd.dispatchImport(84,cpu)&&cpu.gpr[2]==1,"layer-zero lookup failed");
 const auto lsn=memory.read32(0x2400);
 require(lsn>=20&&memory.read32(0x2404)==4,"wrong actual file metadata");
 require(memory.readString(0x2408,16)=="TEST.BIN","wrong file name");
 std::array<uint8_t,32>a{},b{};memory.readRam(0x2400,a.data(),a.size());
 cpu.gpr[4]=0x2500;cdvd.dispatchImport(10,cpu);memory.readRam(0x2500,b.data(),b.size());
 require(a==b,"layer-zero and ordinary search disagree");
 cpu.gpr[6]=1;require(cdvd.dispatchImport(84,cpu)&&cpu.gpr[2]==0,"unsupported layer invented a result");
 const char missing[]="cdrom0:\\DATA\\MISSING.BIN;1";memory.writeRam(0x2480,missing,sizeof(missing));
 cpu.gpr[6]=0;require(cdvd.dispatchImport(84,cpu)&&cpu.gpr[2]==0,"missing file invented");
 cpu.gpr[4]=lsn;cpu.gpr[5]=1;cpu.gpr[6]=buffer;
 require(cdvd.dispatchImport(6,cpu)&&cpu.gpr[2]==1,"real sector read failed");
 require(memory.readString(buffer,4)=="ABCD"&&memory.read8(buffer+4)==0,"sector bytes/padding wrong");
 cdvd.reset();require(!memory.allocationContaining(buffer).has_value(),"reset leaked shared buffer");
 std::cout<<"PASS: opt-out, stable 42128-byte buffer, real case-insensitive layer-zero lookup, metadata, sector bytes, missing/layer rejection, reset release\n";
}
