#include <map>
#include <set>
#include <list>
#include <queue>
#include <fstream>
#include <iostream>
#include <iomanip>

#include <llvm/IR/Module.h>
#include <llvm/IRReader/IRReader.h>
#include <llvm/IR/LLVMContext.h>
#include <llvm/Support/SourceMgr.h>
#include <llvm/Support/CommandLine.h>
#include <llvm/IR/Instructions.h>
#include <llvm/IR/Constants.h>


static llvm::cl::opt<std::string> InputFile(
        "f",
        llvm::cl::desc("Input bc file, Must be Absolute Path"),
        llvm::cl::init(""));

static llvm::cl::opt<std::string> ModInitDB(
        "i",
        llvm::cl::desc("Module init_module function name database (Each entry's file name Must be Absolute Path)"),
        llvm::cl::init(""));

static llvm::cl::opt<std::string> OutputFile(
        "o",
        llvm::cl::desc("Output db file"),
        llvm::cl::init(""));

static llvm::cl::opt<std::string> AliasFile(
        "a",
        llvm::cl::desc("modules.alias file"),
        llvm::cl::init(""));

static llvm::cl::opt<std::string> AllBCs(
        "l",
        llvm::cl::desc("allbc.list file"),
        llvm::cl::init(""));

static std::set<std::string> pci_register_func = {
    /*PCI Drivers*/
    "pci_match_id",
    /*Input Drivers*/
    "input_register_handler",
    /*ACPI*/
    "acpi_scan_add_handler",
    "acpi_scan_add_handler_with_hotplug",
    /*DRM*/
    "drm_legacy_pci_init",
};

static std::map<std::string, std::map<std::string, std::string>> modinit_db;
static std::map<std::string, std::set<std::string>> modcb_db;

template <class T>
T _get_const_int(llvm::Constant *I) {
    if (!I)
        return (T)-1;
    llvm::ConstantInt *ci = llvm::dyn_cast<llvm::ConstantInt>(I);
    if (!ci || ci->getBitWidth() != (sizeof(T)*8))
        return (T)-1;
    return ci->getZExtValue();
}

void _add(std::ofstream &output, std::string del, bool cond, unsigned bw, uint64_t val) {
    if (cond)
        output << del << std::uppercase << std::setfill('0') << std::setw(bw*2) << std::hex << val;
    else
        output << del << "*";
}

void log_err(std::ofstream &errout, const std::string &inputfile, llvm::Constant *v) {
    errout << inputfile << "\n";
}

llvm::Constant *strip_padding(llvm::Constant *st) {
    if (st->getType()->isStructTy() \
            && llvm::dyn_cast<llvm::StructType>(st->getType())->isLiteral()) {
        st = st->getAggregateElement(0u);
    }
    return st;
}

/* Handles increment/decrement of BCD formatted integers */
/* Returns the previous value, so it works like i++ or i-- */
static unsigned int incbcd(unsigned int *bcd,
        int inc,
        unsigned char max,
        size_t chars)
{
    unsigned int init = *bcd, i, j;
    unsigned long long c, dec = 0;

    /* If bcd is not in BCD format, just increment */
    if (max > 0x9) {
        *bcd += inc;
        return init;
    }

    /* Convert BCD to Decimal */
    for (i=0 ; i < chars ; i++) {
        c = (*bcd >> (i << 2)) & 0xf;
        c = c > 9 ? 9 : c; /* force to bcd just in case */
        for (j=0 ; j < i ; j++)
            c = c * 10;
        dec += c;
    }

    /* Do our increment/decrement */
    dec += inc;
    *bcd  = 0;

    /* Convert back to BCD */
    for (i=0 ; i < chars ; i++) {
        for (c=1,j=0 ; j < i ; j++)
            c = c * 10;
        c = (dec / c) % 10;
        *bcd += c << (i << 2);
    }
    return init;
}

std::string get_const_str(llvm::Constant *buf) {
    if (buf->isNullValue())
        return "";
    if (!llvm::isa<llvm::ConstantDataArray>(buf))
        return "";
    llvm::ConstantDataArray *s = llvm::dyn_cast<llvm::ConstantDataArray>(buf);
    if (!s)
        return "";
    return s->getAsString().str().c_str();
}

std::string normalize_str(std::string s, const char *del, const char *rep) {
    size_t pos = 0;
    while ((pos = s.find(del, pos)) != std::string::npos) {
        s.replace(pos, strlen(del), rep);
        pos += strlen(rep);
    }
    return s;
}

void dump_platform_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        if (!e->getAggregateElement(0u)) return;
        if (!llvm::isa<llvm::ConstantDataArray>(e->getAggregateElement(0u))) return;
        llvm::ConstantDataArray *id = llvm::dyn_cast<llvm::ConstantDataArray>(
                e->getAggregateElement(0u));
        if (!id) return;

        output << "platform_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " "
            << "platform:"<< id->getAsString().str().c_str() << "\n";
    }
}

void dump_of_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        if (!e->getType()->getStructName().equals("struct.of_device_id")) return;
        std::string name = get_const_str(e->getAggregateElement(0u));
        std::string type = get_const_str(e->getAggregateElement(1u));
        std::string compat = get_const_str(e->getAggregateElement(2u));
        if (name.empty()) name = "*";
        if (type.empty()) type = "*";
        if (compat.empty()) compat = "*";
        name = normalize_str(name, " ", "_");
        type = normalize_str(type, " ", "_");
        compat = normalize_str(compat, " ", "_");

        output << "of_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " "
            << "of:"<< "N" << name << "T" << type << "C" << compat << "\n";
        output << "of_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " "
            << "of:"<< "N" << name << "T" << type << "C" << compat <<"C*"<< "\n";
    }
}

void dump_acpi_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        if (!e->getType()->getStructName().equals("struct.acpi_device_id")) return;
        std::string id = get_const_str(e->getAggregateElement(0u));
        if (!e->getAggregateElement(2u)) return;
        llvm::ConstantInt *cls = llvm::dyn_cast<llvm::ConstantInt>(e->getAggregateElement(2u));
        llvm::ConstantInt *cls_mask = llvm::dyn_cast<llvm::ConstantInt>(e->getAggregateElement(2u));
        if (!cls || !cls_mask) return;

        if (!id.empty()) {
            output << "acpi_device_id" << " "
                << entrypoint.c_str() << " "
                << modname << " "
                << "acpi*:"<< id << ":*" << "\n";
        } else {
            if (! cls || cls->getBitWidth() != 32) return;
            if (!cls_mask || cls_mask->getBitWidth() != 32) return;
            output << "acpi_device_id" << " "
                << entrypoint.c_str() << " "
                << modname << " "
                << "acpi*:";

            // ?? Starting from 1? (ref: scripts/mod/file2alias.c)
            for (int i = 1; i <= 3; i++) {
                int byte_shift = 8 * (3-i);
                unsigned int msk = (cls_mask->getZExtValue() >> byte_shift) & 0xFF;
                if (msk)
                    output << std::uppercase << std::setfill('0') << std::setw(2) << std::hex << ((cls->getZExtValue() >> byte_shift)&0xFF);
                else
                    output << "??";
            }
            output << ":*\n";
        }
    }
}

void dump_pci_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        if (!e->getType()->getStructName().equals("struct.pci_device_id")) return;
        llvm::Constant *vendor_id = e->getAggregateElement(0u);
        llvm::Constant *device_id = e->getAggregateElement(1u);
        llvm::Constant *subvendor_id = e->getAggregateElement(2u);
        llvm::Constant *subdevice_id = e->getAggregateElement(3u);
        llvm::Constant *cls = e->getAggregateElement(4u);
        llvm::Constant *clsmask = e->getAggregateElement(5u);
        llvm::Constant *ovride = e->getAggregateElement(7u);

        llvm::ConstantInt *vid = llvm::dyn_cast<llvm::ConstantInt>(vendor_id);
        if (!vid) return;
        llvm::ConstantInt *did = llvm::dyn_cast<llvm::ConstantInt>(device_id);
        if (!did) return;
        llvm::ConstantInt *svid = llvm::dyn_cast<llvm::ConstantInt>(subvendor_id);
        if (!svid) return;
        llvm::ConstantInt *sdid = llvm::dyn_cast<llvm::ConstantInt>(subdevice_id);
        if (!sdid) return;
        llvm::ConstantInt *cl = llvm::dyn_cast<llvm::ConstantInt>(cls);
        if (!cl) return;
        llvm::ConstantInt *msk = llvm::dyn_cast<llvm::ConstantInt>(clsmask);
        if (!msk) return;
        llvm::ConstantInt *ovr = llvm::dyn_cast<llvm::ConstantInt>(ovride);
        if (!ovr) return;

        output << "pci_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " ";

        if (ovr->getSExtValue())
            output << "vfio_pci:";
        else
            output << "pci:";

        // Check PCI_ANY_ID
        _add(output, "v", vid->getSExtValue() != -1, 4, vid->getZExtValue());
        _add(output, "d", did->getSExtValue() != -1, 4, did->getZExtValue());
        _add(output, "sv", svid->getSExtValue() != -1, 4, svid->getZExtValue());
        _add(output, "sd", sdid->getSExtValue() != -1, 4, sdid->getZExtValue());

        // Check Class
        unsigned char baseclass = (cl->getZExtValue()) >> 16;
        unsigned char baseclass_mask = (msk->getZExtValue()) >> 16;
        unsigned char subclass = (cl->getZExtValue()) >> 8;
        unsigned char subclass_mask = (msk->getZExtValue()) >> 8;
        unsigned char interface = cl->getZExtValue();
        unsigned char interface_mask = msk->getZExtValue();
        _add(output, "bc", baseclass_mask == 0xff, 1, baseclass);
        _add(output, "sc", subclass_mask == 0xff, 1, subclass);
        _add(output, "i", interface_mask == 0xff, 1, interface);
        if (interface_mask == 0xff)
            output << "*";
        output << "\n";
    }
}

#define do_usb_entry(bcdDevice_initial, bcdDevice_initial_digits, \
        range_lo, range_hi, max)    \
        output << "usb_device_id" << " "    \
        << entrypoint.c_str() << " "    \
        << modname << " ";  \
        output << "usb:";   \
        _add(output, "v", match_flags&0x1/*USB_DEVICE_ID_MATCH_VENDOR*/, 2, idVendor); \
        _add(output, "p", match_flags&0x2/*USB_DEVICE_ID_MATCH_PRODUCT*/, 2, idProduct); \
        output << "d";  \
        if (bcdDevice_initial_digits) \
        output << std::uppercase << std::setfill('0') << std::setw(bcdDevice_initial_digits) << std::hex << bcdDevice_initial;  \
        if (range_lo == range_hi)   \
        output << std::uppercase << std::hex << (int)range_lo; \
        else if (range_lo > 0 || range_hi < max) {  \
            if (range_lo > 0x9 || range_hi < 0xA)   \
            output << "[" << std::uppercase << std::hex << (int)range_lo << "-" << std::uppercase << std::hex << (int)range_hi << "]";    \
            else {  \
                if (range_lo < 0x9) \
                output << "[" << std::uppercase << std::hex << (int)range_lo << "-9";    \
                else    \
                output << "[" << std::uppercase << std::hex << (int)range_lo;    \
                if (range_hi > 0xA) \
                output << "A-" << std::uppercase << std::hex << (int)range_hi << "]";    \
                else    \
                output << std::uppercase << std::hex << (int)range_hi << "]";    \
            }   \
        }   \
        if (bcdDevice_initial_digits < (sizeof(bcdDevice_lo) * 2 - 1))  \
        output << "*";  \
        _add(output, "dc", match_flags&0x10/*USB_DEVICE_ID_MATCH_DEV_CLASS*/, 1, bDeviceClass); \
        _add(output, "dsc", match_flags&0x20/*USB_DEVICE_ID_MATCH_DEV_SUBCLASS*/, 1, bDeviceSubClass);  \
        _add(output, "dp", match_flags&0x40/*USB_DEVICE_ID_MATCH_DEV_PROTOCOL*/, 1, bDeviceProtocol);   \
        _add(output, "ic", match_flags&0x80/*USB_DEVICE_ID_MATCH_INT_CLASS*/, 1, bInterfaceClass);  \
        _add(output, "isc", match_flags&0x100/*USB_DEVICE_ID_MATCH_INT_SUBCLASS*/, 1, bInterfaceSubClass);  \
        _add(output, "ip", match_flags&0x200/*USB_DEVICE_ID_MATCH_INT_PROTOCOL*/, 1, bInterfaceProtocol);   \
        _add(output, "in", match_flags&0x400/*USB_DEVICE_ID_MATCH_INT_NUMBER*/, 1, bInterfaceNumber);   \
        if (match_flags&0x400)    \
        output << "*";  \
        output << "\n";

void dump_usb_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        if (!e->getType()->getStructName().equals("struct.usb_device_id")) return;
        uint16_t match_flags = _get_const_int<uint16_t>(e->getAggregateElement(0u));
        if (match_flags == (uint16_t)-1) return;
        uint16_t idVendor = _get_const_int<uint16_t>(e->getAggregateElement(1u));
        if (idVendor == (uint16_t)-1) return;
        uint16_t idProduct = _get_const_int<uint16_t>(e->getAggregateElement(2u));
        if (idProduct == (uint16_t)-1) return;
        uint16_t bcdDevice_lo = _get_const_int<uint16_t>(e->getAggregateElement(3u));
        if (bcdDevice_lo == (uint16_t)-1) return;
        uint16_t bcdDevice_hi = _get_const_int<uint16_t>(e->getAggregateElement(4u));
        if (bcdDevice_hi == (uint16_t)-1) return;
        uint8_t bDeviceClass = _get_const_int<uint8_t>(e->getAggregateElement(5u));
        if (bDeviceClass == (uint8_t)-1) return;
        uint8_t bDeviceSubClass = _get_const_int<uint8_t>(e->getAggregateElement(6u));
        if (bDeviceSubClass == (uint8_t)-1) return;
        uint8_t bDeviceProtocol = _get_const_int<uint8_t>(e->getAggregateElement(7u));
        if (bDeviceProtocol == (uint8_t)-1) return;
        uint8_t bInterfaceClass = _get_const_int<uint8_t>(e->getAggregateElement(8u));
        if (bInterfaceClass == (uint8_t)-1) return;
        uint8_t bInterfaceSubClass = _get_const_int<uint8_t>(e->getAggregateElement(9u));
        if (bInterfaceSubClass == (uint8_t)-1) return;
        uint8_t bInterfaceProtocol = _get_const_int<uint8_t>(e->getAggregateElement(10u));
        if (bInterfaceProtocol == (uint8_t)-1) return;
        uint8_t bInterfaceNumber = _get_const_int<uint8_t>(e->getAggregateElement(11u));
        if (bInterfaceNumber == (uint8_t)-1) return;

        unsigned int devlo, devhi;
        uint8_t chi, clo, max;
        int ndigits;
        devlo = match_flags & 4/*USB_DEVICE_ID_MATCH_DEV_LO*/ ?
            bcdDevice_lo : 0x0U;
        devhi = match_flags & 8/*USB_DEVICE_ID_MATCH_DEV_HI*/ ?
            bcdDevice_hi : ~0x0U;
        /* Figure out if this entry is in bcd or hex format */
        max = 0x9; /* Default to decimal format */
        for (ndigits = 0 ; ndigits < sizeof(bcdDevice_lo) * 2 ; ndigits++) {
            clo = (devlo >> (ndigits << 2)) & 0xf;
            chi = ((devhi > 0x9999 ? 0x9999 : devhi) >> (ndigits << 2)) & 0xf;
            if (clo > max || chi > max) {
                max = 0xf;
                break;
            }
        }
        /* Convert numeric bcdDevice range into fnmatch-able pattern(s) */
        for (ndigits = sizeof(bcdDevice_lo) * 2 - 1; devlo <= devhi; ndigits--) {
            clo = devlo & 0xf;
            chi = devhi & 0xf;
            if (chi > max)	/* If we are in bcd mode, truncate if necessary */
                chi = max;
            devlo >>= 4;
            devhi >>= 4;

            if (devlo == devhi || !ndigits) {
                do_usb_entry(devlo, ndigits, clo, chi, max);
                break;
            }

            if (clo > 0x0) {
                do_usb_entry(incbcd(&devlo, 1, max,
                            sizeof(bcdDevice_lo) * 2),
                        ndigits, clo, max, max);
            }

            if (chi < max) {
                do_usb_entry(incbcd(&devhi, -1, max,
                            sizeof(bcdDevice_lo) * 2),
                        ndigits, 0x0, chi, max);
            }
        }
    }
}

void dump_virtio_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        uint32_t device = _get_const_int<uint32_t>(e->getAggregateElement(0u));
        if (device == (uint32_t)-1) return;
        uint32_t vendor = _get_const_int<uint32_t>(e->getAggregateElement(1u));
        if (vendor == (uint32_t)-1) return;

        output << "virtio_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " ";

        output << "virtio:";
        _add(output, "d", device != 0xffffffff/*VIRTIO_DEV_ANY_ID*/, 4, device);
        _add(output, "v", vendor != 0xffffffff/*VIRTIO_DEV_ANY_ID*/, 4, vendor);
        if (vendor != 0xffffffff)
            output << "*";
        output << "\n";
    }
}

void dump_vmbus_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        if (!e->getType()->getStructName().equals("struct.hv_vmbus_device_id")) return;
        llvm::Constant *idstruct = e->getAggregateElement(0u);
        llvm::Constant *guid = idstruct->getAggregateElement(0u);
        if (!guid->getType()->isArrayTy()) return;

        llvm::ConstantDataArray *guid_data = llvm::dyn_cast<llvm::ConstantDataArray>(guid);
        if (!guid_data) return;

        output << "hv_vmbus_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " ";

        output << "vmbus:";
        for (unsigned j = 0; j < guid_data->getRawDataValues().size(); j++) {
            output << std::nouppercase << std::setfill('0') << std::setw(2) << guid_data->getElementAsInteger(j);
        }
        output << "\n";
    }
}

void dump_xenbus_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        if (!e->getType()->getStructName().equals("struct.xenbus_device_id")) return;
        llvm::Constant *idesc = e->getAggregateElement(0u);
        if (!idesc->getType()->isArrayTy()) return;
        std::string xendesc = llvm::dyn_cast<llvm::ConstantDataArray>(idesc)->getAsString().str().c_str(); 

        output << "xenbus_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " "
            << "xen:" << xendesc << "\n";
    }
}

void dump_i2c_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        llvm::Constant *idesc = e->getAggregateElement(0u);
        if (!idesc->getType()->isArrayTy()) return;
        std::string name = llvm::dyn_cast<llvm::ConstantDataArray>(idesc)->getAsString().str().c_str(); 

        output << "i2c_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " "
            << "i2c:" << name << "\n";
    }
}

void dump_spi_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;
        if (!e->getType()->getStructName().equals("struct.spi_device_id")) return;
        llvm::Constant *idesc = e->getAggregateElement(0u);
        if (!idesc->getType()->isArrayTy()) return;
        std::string name = llvm::dyn_cast<llvm::ConstantDataArray>(idesc)->getAsString().str().c_str(); 

        output << "spi_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " "
            << "spi:" << name << "\n";
    }
}

static inline void __endian(const void *src, void *dest, unsigned int size)
{
    unsigned int i;
    for (i = 0; i < size; i++)
        ((unsigned char*)dest)[i] = ((unsigned char*)src)[size - i-1];
}

static void do_input(std::ofstream &output, llvm::Constant *arr, unsigned int min) {
    unsigned int i;
    uint64_t bits = sizeof(uint64_t)*8;
    llvm::Constant *e;
    for (i = min; e = arr->getAggregateElement(i/bits); i++) {
        if (e->isNullValue()) continue;
        uint64_t ent = _get_const_int<uint64_t>(e);
        if (ent == (uint64_t)-1) continue;
        uint64_t nent = ent;
        if (nent & (1L << (i%bits)))
            output << std::uppercase << std::hex << i << ",*";
    }
}

void dump_input_id(llvm::Constant *idtab, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *e;
    for (unsigned i = 0; e = idtab->getAggregateElement(i); i++) {
        if (e->isNullValue()) return;
        if (!e->getType()->isStructTy()) return;

        unsigned long flags = _get_const_int<unsigned long>(e->getAggregateElement(0u));
        if (flags == (unsigned long)-1) return;
        uint16_t bustype = _get_const_int<uint16_t>(e->getAggregateElement(1u));
        if (bustype == (uint16_t)-1) return;
        uint16_t vendor = _get_const_int<uint16_t>(e->getAggregateElement(2u));
        if (vendor == (uint16_t)-1) return;
        uint16_t product = _get_const_int<uint16_t>(e->getAggregateElement(3u));
        if (product == (uint16_t)-1) return;
        uint16_t version = _get_const_int<uint16_t>(e->getAggregateElement(4u));
        if (version == (uint16_t)-1) return;

        llvm::Constant *evbit = e->getAggregateElement(5u);
        llvm::Constant *keybit = e->getAggregateElement(6u);
        llvm::Constant *relbit = e->getAggregateElement(7u);
        llvm::Constant *absbit = e->getAggregateElement(8u);
        llvm::Constant *mscbit = e->getAggregateElement(9u);
        llvm::Constant *ledbit = e->getAggregateElement(10u);
        llvm::Constant *sndbit = e->getAggregateElement(11u);
        llvm::Constant *ffbit = e->getAggregateElement(12u);
        llvm::Constant *swbit = e->getAggregateElement(13u);

#define INPUT_DEVICE_ID_MATCH_BUS	1
#define INPUT_DEVICE_ID_MATCH_VENDOR	2
#define INPUT_DEVICE_ID_MATCH_PRODUCT	4
#define INPUT_DEVICE_ID_MATCH_VERSION	8

#define INPUT_DEVICE_ID_MATCH_EVBIT	0x0010
#define INPUT_DEVICE_ID_MATCH_KEYBIT	0x0020
#define INPUT_DEVICE_ID_MATCH_RELBIT	0x0040
#define INPUT_DEVICE_ID_MATCH_ABSBIT	0x0080
#define INPUT_DEVICE_ID_MATCH_MSCIT	0x0100
#define INPUT_DEVICE_ID_MATCH_LEDBIT	0x0200
#define INPUT_DEVICE_ID_MATCH_SNDBIT	0x0400
#define INPUT_DEVICE_ID_MATCH_FFBIT	0x0800
#define INPUT_DEVICE_ID_MATCH_SWBIT	0x1000
#define INPUT_DEVICE_ID_MATCH_PROPBIT	0x2000

        output << "input_device_id" << " "
            << entrypoint.c_str() << " "
            << modname << " "
            << "input:";
        _add(output, "b", flags & INPUT_DEVICE_ID_MATCH_BUS, 2, bustype);
        _add(output, "v", flags & INPUT_DEVICE_ID_MATCH_VENDOR, 2, vendor);
        _add(output, "p", flags & INPUT_DEVICE_ID_MATCH_PRODUCT, 2, product);
        _add(output, "e", flags & INPUT_DEVICE_ID_MATCH_VERSION, 2, version);
        output << "-e*";

        if (flags & INPUT_DEVICE_ID_MATCH_EVBIT)
            do_input(output, evbit, 0);
        output << "k*";
        if (flags & INPUT_DEVICE_ID_MATCH_KEYBIT)
            do_input(output, keybit,
                    0x71 /*INPUT_DEVICE_ID_KEY_MIN_INTERESTING*/);
        output << "r*";
        if (flags & INPUT_DEVICE_ID_MATCH_RELBIT)
            do_input(output, relbit, 0);
        output << "a*";
        if (flags & INPUT_DEVICE_ID_MATCH_ABSBIT)
            do_input(output, absbit, 0);
        output << "m*";
        if (flags & INPUT_DEVICE_ID_MATCH_MSCIT)
            do_input(output, mscbit, 0);
        output << "l*";
        if (flags & INPUT_DEVICE_ID_MATCH_LEDBIT)
            do_input(output, ledbit, 0);
        output << "s*";
        if (flags & INPUT_DEVICE_ID_MATCH_SNDBIT)
            do_input(output, sndbit, 0);
        output << "f*";
        if (flags & INPUT_DEVICE_ID_MATCH_FFBIT)
            do_input(output, ffbit, 0);
        output << "w*";
        if (flags & INPUT_DEVICE_ID_MATCH_SWBIT)
            do_input(output, swbit, 0);
        output << "\n";
    }
}

void _handle_platform(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output);
void handle_platform(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *devdrv = desc->getAggregateElement(5u);
    llvm::Constant *plat_idtab = desc->getAggregateElement(6u);
    if (devdrv->isNullValue() || plat_idtab->isNullValue()) return;
    if (!llvm::isa<llvm::ConstantPointerNull>(plat_idtab)) {
        auto *plat_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(plat_idtab);
        if (!plat_idtab_gv || !plat_idtab_gv->hasInitializer())
            return;
        llvm::Constant *id_tab = plat_idtab_gv->getInitializer();
        if (!id_tab) return;
        id_tab = strip_padding(id_tab); // Avoid Literal Struct Type (Padding)
        if (!id_tab->getType()->isArrayTy()) return;
        dump_platform_id(id_tab, entrypoint, modname, output);
    }

    _handle_platform(devdrv, entrypoint, modname, output);
}

void _handle_platform(llvm::Constant *devdrv, std::string entrypoint, std::string modname, std::ofstream &output) {

    if (devdrv->isNullValue()) return;

    devdrv = strip_padding(devdrv);
    if (!devdrv->getType()->getStructName().equals("struct.device_driver")
            && !devdrv->getType()->getStructName().startswith("struct.device_driver."))
        return;

    llvm::Constant *name = devdrv->getAggregateElement(0u);
    llvm::Constant *of_id = devdrv->getAggregateElement(6u);
    llvm::Constant *acpi_id = devdrv->getAggregateElement(7u);

    if (name->isNullValue() || of_id->isNullValue() || acpi_id->isNullValue())
        return;

    if (!llvm::isa<llvm::ConstantPointerNull>(name)) {
        auto *name_gv = llvm::dyn_cast<llvm::GlobalVariable>(name);
        if (!name_gv || !name_gv->hasInitializer())
            return;
        llvm::Constant *namedata = name_gv->getInitializer();
        if (!namedata) return;
        namedata = strip_padding(namedata);
        std::string namestr = get_const_str(namedata);
        std::replace(namestr.begin(), namestr.end(), ' ', '_');
        output << "platform_name" << " "
            << entrypoint.c_str() << " "
            << modname << " "
            << "platform:" << namestr << "\n";
    }
    if (!llvm::isa<llvm::ConstantPointerNull>(of_id)) {
        auto *of_id_gv = llvm::dyn_cast<llvm::GlobalVariable>(of_id);
        if (!of_id_gv || !of_id_gv->hasInitializer())
            return;
        llvm::Constant *id_tab = of_id_gv->getInitializer();
        if (!id_tab) return;
        id_tab = strip_padding(id_tab);
        if (!id_tab->getType()->isArrayTy()) return;
        dump_of_id(id_tab, entrypoint, modname, output);
    }
    if (!llvm::isa<llvm::ConstantPointerNull>(acpi_id)) {
        auto *acpi_id_gv = llvm::dyn_cast<llvm::GlobalVariable>(acpi_id);
        if (!acpi_id_gv || !acpi_id_gv->hasInitializer())
            return;
        llvm::Constant *id_tab = acpi_id_gv->getInitializer();
        if (!id_tab) return;
        id_tab = strip_padding(id_tab);
        if (!id_tab->getType()->isArrayTy()) return;
        dump_acpi_id(id_tab, entrypoint, modname, output);
    }
    return;
}

void handle_pci(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *desc_idtab = desc->getAggregateElement(2u);
    if (desc_idtab->isNullValue()) return;
    if (llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) return;
    if (!llvm::isa<llvm::GlobalVariable>(desc_idtab)) return;
    auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
    if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
        return;
    llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
    if (!id_tab) return;
    id_tab = strip_padding(id_tab);
    if (!id_tab->getType()->isArrayTy()) return;
    dump_pci_id(id_tab, entrypoint, modname, output);
}

void handle_usb(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *desc_idtab = desc->getAggregateElement(9u);
    if (desc_idtab->isNullValue())
        return;
    if (llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) return;
    auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
    if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
        return;
    llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
    if (!id_tab) return;
    id_tab = strip_padding(id_tab);
    if (!id_tab->getType()->isArrayTy()) return;
    dump_usb_id(id_tab, entrypoint, modname, output);
}

void handle_usb_serial(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *desc_idtab = desc->getAggregateElement(1u);
    if (desc_idtab->isNullValue()) return;
    if (llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) return;
    auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
    if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
        return;
    llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
    if (!id_tab) return;
    id_tab = strip_padding(id_tab);
    if (!id_tab->getType()->isArrayTy()) return;
    dump_usb_id(id_tab, entrypoint, modname, output);
}

void handle_virtio(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *desc_idtab = desc->getAggregateElement(1u);
    if (desc_idtab->isNullValue()) return;
    if (llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) return;
    auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
    if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
        return;
    llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
    if (!id_tab) return;
    id_tab = strip_padding(id_tab);
    if (!id_tab->getType()->isArrayTy()) return;
    dump_virtio_id(id_tab, entrypoint, modname, output);
}

void handle_vmbus(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *desc_idtab = desc->getAggregateElement(3u);
    if (desc_idtab->isNullValue()) return;
    if (llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) return;
    auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
    if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
        return;
    llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
    if (!id_tab) return;
    id_tab = strip_padding(id_tab);
    if (!id_tab->getType()->isArrayTy()) return;
    dump_vmbus_id(id_tab, entrypoint, modname, output);
}

void handle_xenbus(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *desc_idtab = desc->getAggregateElement(1u);
    if (desc_idtab->isNullValue()) return;
    if (llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) return;
    auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
    if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
        return;
    llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
    if (!id_tab) return;
    id_tab = strip_padding(id_tab);
    if (!id_tab->getType()->isArrayTy()) return;
    dump_xenbus_id(id_tab, entrypoint, modname, output);
}

void handle_i2c(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *devdrv = desc->getAggregateElement(7u);
    llvm::Constant *desc_idtab = desc->getAggregateElement(8u);
    if (devdrv->isNullValue() || desc_idtab->isNullValue()) return;
    if (!llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) {
        auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
        if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
            return;
        llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
        if (!id_tab) return;
        id_tab = strip_padding(id_tab);
        if (!id_tab->getType()->isArrayTy()) return;
        dump_i2c_id(id_tab, entrypoint, modname, output);
    }

    // acpi/of id match
    if (devdrv->isNullValue())  return;

    devdrv = strip_padding(devdrv);
    if (!devdrv->getType()->getStructName().equals("struct.device_driver"))
        return;

    llvm::Constant *of_id = devdrv->getAggregateElement(6);
    llvm::Constant *acpi_id = devdrv->getAggregateElement(7);
    if (of_id->isNullValue() || acpi_id->isNullValue())
        return;

    if (!llvm::isa<llvm::ConstantPointerNull>(of_id)) {
        if (!llvm::isa<llvm::GlobalVariable>(of_id)) return;
        llvm::GlobalVariable *gidtab = llvm::dyn_cast<llvm::GlobalVariable>(of_id);
        if (!gidtab) return;
        if (gidtab->hasInitializer()) {
            llvm::Constant *id_tab = llvm::dyn_cast<llvm::GlobalVariable>(of_id)->getInitializer();
            if (!id_tab)
                return;
            id_tab = strip_padding(id_tab);
            if (!id_tab->getType()->isArrayTy()) return;
            dump_of_id(id_tab, entrypoint, modname, output);
        }
    }
    if (!llvm::isa<llvm::ConstantPointerNull>(acpi_id)) {
        if (!llvm::isa<llvm::GlobalVariable>(acpi_id)) return;
        auto *acpi_id_gv = llvm::dyn_cast<llvm::GlobalVariable>(acpi_id);
        if (!acpi_id_gv || !acpi_id_gv->hasInitializer())
            return;
        llvm::Constant *id_tab = acpi_id_gv->getInitializer();
        if (!id_tab) return;
        id_tab = strip_padding(id_tab);
        if (!id_tab->getType()->isArrayTy()) return;
        dump_acpi_id(id_tab, entrypoint, modname, output);
    }
    return;
}

void handle_spi(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *devdrv = desc->getAggregateElement(4u);
    llvm::Constant *desc_idtab = desc->getAggregateElement(0u);
    if (devdrv->isNullValue() || desc_idtab->isNullValue())
        return;
    if (!llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) {
        auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
        if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
            return;
        llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
        if (!id_tab) return;
        id_tab = strip_padding(id_tab);
        if (!id_tab->getType()->isArrayTy()) return;
        dump_spi_id(id_tab, entrypoint, modname, output);
    }

    // acpi/of id match
    if (devdrv->isNullValue())  return;

    devdrv = strip_padding(devdrv);
    if (!devdrv->getType()->getStructName().equals("struct.device_driver"))
        return;

    llvm::Constant *of_id = devdrv->getAggregateElement(6);
    llvm::Constant *acpi_id = devdrv->getAggregateElement(7);
    if (of_id->isNullValue() || acpi_id->isNullValue())
        return;
    if (!llvm::isa<llvm::ConstantPointerNull>(of_id)) {
        if (!llvm::isa<llvm::GlobalVariable>(of_id))
            return;
        llvm::GlobalVariable *gidtab = llvm::dyn_cast<llvm::GlobalVariable>(of_id);
        if (!gidtab)
            return;
        if (gidtab->hasInitializer()) {
            llvm::Constant *id_tab = llvm::dyn_cast<llvm::GlobalVariable>(of_id)->getInitializer();
            if (!id_tab)
                return;
            id_tab = strip_padding(id_tab);
            if (!id_tab->getType()->isArrayTy())
                return;
            dump_of_id(id_tab, entrypoint, modname, output);
        }
    }
    if (!llvm::isa<llvm::ConstantPointerNull>(acpi_id)) {
        auto *acpi_id_gv = llvm::dyn_cast<llvm::GlobalVariable>(acpi_id);
        if (!acpi_id_gv || !acpi_id_gv->hasInitializer())
            return;
        llvm::Constant *id_tab = acpi_id_gv->getInitializer();
        if (!id_tab)
            return;
        id_tab = strip_padding(id_tab);
        if (!id_tab->getType()->isArrayTy())
            return;
        dump_acpi_id(id_tab, entrypoint, modname, output);
    }
    return;
}

void handle_input(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *desc_idtab = desc->getAggregateElement(11u);
    if (desc_idtab->isNullValue())
        return;
    if (llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) return;
    auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
    if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
        return;
    llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
    if (!id_tab)
        return;
    id_tab = strip_padding(id_tab);
    if (!id_tab->getType()->isArrayTy())
        return;
    dump_input_id(id_tab, entrypoint, modname, output);
}

void handle_misc_acpi(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *desc_idtab = desc->getAggregateElement(0u);
    if (desc_idtab->isNullValue())
        return;
    if (llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) return;
    auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
    if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
        return;
    llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
    if (!id_tab)
        return;
    id_tab = strip_padding(id_tab);
    if (!id_tab->getType()->isArrayTy())
        return;
    dump_acpi_id(id_tab, entrypoint, modname, output);
}

void handle_acpi(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    llvm::Constant *desc_idtab = desc->getAggregateElement(2u);
    if (desc_idtab->isNullValue())
        return;
    if (llvm::isa<llvm::ConstantPointerNull>(desc_idtab)) return;
    auto *desc_idtab_gv = llvm::dyn_cast<llvm::GlobalVariable>(desc_idtab);
    if (!desc_idtab_gv || !desc_idtab_gv->hasInitializer())
        return;
    llvm::Constant *id_tab = desc_idtab_gv->getInitializer();
    if (!id_tab)
        return;
    id_tab = strip_padding(id_tab);
    if (!id_tab->getType()->isArrayTy())
        return;
    dump_acpi_id(id_tab, entrypoint, modname, output);
}

int driver_dispatch(llvm::Constant *desc, std::string entrypoint, std::string modname, std::ofstream &output) {
    if (modname.empty())    modname = ".builtin";
    llvm::StringRef ty = desc->getType()->getStructName();
    // Extract module name && (global) id table
    if (ty.equals("struct.platform_driver"))
        handle_platform(desc, entrypoint, modname, output);
    else if (ty.equals("struct.device_driver"))
        _handle_platform(desc, entrypoint, modname, output);
    else if (ty.equals("struct.pci_driver"))
        handle_pci(desc, entrypoint, modname, output);
    else if (ty.equals("struct.usb_driver"))
        handle_usb(desc, entrypoint, modname, output);
    else if (ty.equals("struct.usb_serial_driver"))
        handle_usb_serial(desc, entrypoint, modname, output);
    else if (ty.equals("struct.virtio_driver"))
        handle_virtio(desc, entrypoint, modname, output);
    else if (ty.equals("struct.hv_driver"))
        handle_vmbus(desc, entrypoint, modname, output);
    else if (ty.equals("struct.xenbus_driver"))
        handle_xenbus(desc, entrypoint, modname, output);
    else if (ty.equals("struct.i2c_driver"))
        handle_i2c(desc, entrypoint, modname, output);
    else if (ty.equals("struct.spi_driver"))
        handle_spi(desc, entrypoint, modname, output);
    else if (ty.equals("struct.input_handler"))
        handle_input(desc, entrypoint, modname, output);
    else if (ty.equals("struct.acpi_scan_handler"))
        handle_misc_acpi(desc, entrypoint, modname, output);
    else if (ty.equals("struct.acpi_driver"))
        handle_acpi(desc, entrypoint, modname, output);
    else
        return -1;

    return 0;
}

void dispatch_callinst(llvm::CallBase *call, const std::string &inputfile, std::string entrypoint, std::string modname, std::ofstream &output, std::ofstream &errout) {
    int retcode = 0;
    int argidx = 0;
    // Fixup: i2c register has THIS_MODULE as 1st arg
    if (call->getCalledOperand()->getName().equals("i2c_register_driver"))
        argidx = 1;
    // Fixup: spi register has THIS_MODULE as 1st arg
    if (call->getCalledOperand()->getName().equals("__spi_register_driver"))
        argidx = 1;
    // Fixup
    if (call->getCalledOperand()->getName().equals("drm_legacy_pci_init"))
        argidx = 1;
    // Find global struct definition
    if (argidx >= call->arg_size())
        return;
    llvm::Value *arg = call->getArgOperand(argidx)->stripPointerCasts();
    if (arg == NULL)
        return;
    if (!llvm::isa<llvm::GlobalVariable>(arg)) {
        errout << inputfile << "\n";
        std::queue<llvm::User*> wq;
        std::set<llvm::User*> seen({call});
        for (auto &use : arg->uses()) {
            wq.push(use.getUser());
        }
        while (!wq.empty()) {
            llvm::User *u = wq.front();
            wq.pop();
            if (seen.find(u) != seen.end())
                continue;
            seen.insert(u);
            if (llvm::isa<llvm::GlobalVariable>(u)) {
                arg = llvm::dyn_cast<llvm::GlobalVariable>(u);
                break;
            }
            if (llvm::isa<llvm::PHINode>(u)) {
                llvm::PHINode *phi = llvm::dyn_cast<llvm::PHINode>(u);
                for (auto &iv : phi->incoming_values()) {
                    wq.push(iv.getUser());
                }
            }
        }
        if (!arg || !llvm::isa<llvm::GlobalVariable>(arg))
            return;
    }
    if (!llvm::isa<llvm::GlobalVariable>(arg))
        return;
    llvm::GlobalVariable *ptr = llvm::dyn_cast<llvm::GlobalVariable>(arg);
    if (!ptr)
        return;
    if (!ptr->hasInitializer())
        return;
    llvm::Constant *pcidesc = ptr->getInitializer();

    // Avoid Padding/Literal Struct Type (Maybe just `getAggregateElement(0)`)
    pcidesc = strip_padding(pcidesc);

    if (pcidesc->getType()->isStructTy()) {
        retcode = driver_dispatch(pcidesc, entrypoint, modname, output);
        if (retcode)
            log_err(errout, inputfile, pcidesc);
    } else if (pcidesc->getType()->isArrayTy()) {
        llvm::Type* elemty = pcidesc->getType()->getArrayElementType();
        if (elemty->isStructTy() && elemty->getStructName().equals("struct.pci_device_id")) {
            dump_pci_id(pcidesc, entrypoint, modname, output);
            return;
        }
        llvm::Constant *pdrv, *drv;
        for (int i = 0; pdrv = pcidesc->getAggregateElement(i); i++) {
            if (!pdrv)   break;
            if (llvm::isa<llvm::ConstantPointerNull>(pdrv)) break;
            if (!llvm::isa<llvm::GlobalVariable>(pdrv)) {
                log_err(errout, inputfile, pdrv);
                continue;
            }

            auto *pdrv_gv = llvm::dyn_cast<llvm::GlobalVariable>(pdrv);
            if (!pdrv_gv || !pdrv_gv->hasInitializer())
                return;

            drv = strip_padding(pdrv_gv->getInitializer());
            retcode = driver_dispatch(drv, entrypoint, modname, output);
            if (retcode)
                log_err(errout, inputfile, drv);
        }
    } else {
        assert (false);
    }
}

void processModuleFile(const std::string &inputfile, std::ofstream &output, std::ofstream &errout) {
    llvm::SMDiagnostic err;
    llvm::LLVMContext context;
    llvm::outs() << inputfile << "\n";
    std::unique_ptr<llvm::Module> module = llvm::parseIRFile(inputfile, err, context);
    if (!module)    return;

    // PreProfile Module
    std::set<llvm::CallBase*> regcalls;
    for (auto func = module->begin(); func != module->end(); func++) {
        for (auto bb = func->begin(); bb != func->end(); bb++) {
            for (auto inst = bb->begin(); inst != bb->end(); inst++) {
                llvm::Instruction *i = &(*inst);
                if(llvm::isa<llvm::CallBase>(i)) {
                    llvm::CallBase *call = llvm::dyn_cast<llvm::CallBase>(i);
                    if (call->isInlineAsm() || call->isIndirectCall())    continue;
                    //  %call6 = call i32 null(ptr noundef %skb, ptr noundef %data.i)
                    if (!call->getCalledOperand())
                        continue;
                    if (llvm::isa<llvm::ConstantPointerNull>(call->getCalledOperand())) continue;
                    if (pci_register_func.find(call->getCalledOperand()->getName().str()) \
                            != pci_register_func.end()) {
                        regcalls.insert(call);
                    }
                }
            }
        }
    }

    // Find Init Function
    for (auto cbit : modinit_db[inputfile]) {
        std::string entrypoint = cbit.first;
        std::string modname = cbit.second;
        llvm::Function *func = nullptr;

        llvm::outs() << entrypoint << ", " << modname << "\n";
        for (auto funcit = module->begin(); funcit != module->end(); funcit++) {
            if (funcit->getName().equals(entrypoint)) {
                func = &(*funcit);
                break;
            }
        }
        for (auto funcit = module->begin(); !func && funcit != module->end(); funcit++) {
            if (funcit->getName().equals(entrypoint+"_init")) {
                func = &(*funcit);
                entrypoint = entrypoint + "_init";
                break;
            }
        }
        for (auto funcit = module->begin(); !func && funcit != module->end(); funcit++) {
            if (funcit->getName().equals(entrypoint+"_driver_init")) {
                func = &(*funcit);
                entrypoint = entrypoint + "_driver_init";
                break;
            }
        }
        // USB special Case
        for (auto funcit = module->begin(); !func && funcit != module->end(); funcit++) {
            if (funcit->getName().equals("usb_serial_module_init")) {
                func = &(*funcit);
                entrypoint = "usb_serial_module_init";
                break;
            }
        }
        for (auto funcit = module->begin(); !func && funcit != module->end(); funcit++) {
            if (funcit->getName().equals("init_module")) {
                func = &(*funcit);
                break;
            }
        }
        if (!func) {
            errout << inputfile << " " << entrypoint << " " << modname <<"\n";
            return;
        }

        std::list<llvm::Function*>    wq = {func};
        std::set<llvm::Function*>   processed;
        while (!wq.empty()) {
            func = wq.front();
            wq.pop_front();
            processed.insert(func);

            for (auto bb = func->begin(); bb != func->end(); bb++) {
                for (auto inst = bb->begin(); inst != bb->end(); inst++) {
                    llvm::Instruction *i = &(*inst);
                    if(llvm::isa<llvm::CallBase>(i)) {
                        llvm::CallBase *call = llvm::dyn_cast<llvm::CallBase>(i);
                        if (call->isInlineAsm() || call->isIndirectCall())    continue;
                        //  %call6 = call i32 null(ptr noundef %skb, ptr noundef %data.i)
                        if (!call->getCalledOperand())
                            continue;
                        if (llvm::isa<llvm::ConstantPointerNull>(call->getCalledOperand())) continue;

                        llvm::Function *callee = call->getCalledFunction();
                        if (callee && processed.find(callee) == processed.end())
                            wq.push_back(callee);

                        if (pci_register_func.find(call->getCalledOperand()->getName().str()) \
                                != pci_register_func.end()) {

                            regcalls.erase(call);
                            try {
                                dispatch_callinst(call, inputfile, entrypoint, modname, output, errout);
                            }
                            catch (std::domain_error& e) {
                                continue;
                            }
                        }
                    }
                }
            }
        }
    }

    // Fixup Driver/Module
    if (!regcalls.empty() && inputfile.find(".mod.bcmerged") != std::string::npos) {
        for (auto call : regcalls) {
            llvm::outs() << "Fixup " << inputfile <<"\n";
            for (auto cbit : modinit_db[inputfile]) {
                std::string entrypoint = cbit.first;
                std::string modname = cbit.second;
                dispatch_callinst(call, inputfile, entrypoint, modname, output, errout);
            }
        }
        return;
    }

    // Final Check Completeness (Built-in only)
    if (!regcalls.empty()) {
        errout << inputfile << " :\n";
        for (auto call : regcalls) {
            std::string ts;
            llvm::raw_string_ostream rs(ts);
            call->print(rs);
            errout << ts << "\n";
        }
    }
}

int main(int argc, char **argv) {
    llvm::cl::ParseCommandLineOptions(argc, argv, "build PCI driver database\n");

    std::ofstream db(OutputFile);
    std::ofstream err("err.log");

    if (!ModInitDB.empty()) {
        std::ifstream moddb(ModInitDB);
        for (std::string line; std::getline(moddb, line);) {
            std::string name = line.substr(0, line.find(':'));
            std::string initcb = line.substr(line.find(':')+1, line.find(',')-line.find(':')-1);
            std::string modname = line.substr(line.find(',')+1);
            std::string alias = modname.substr(modname.find(',')+1);
            modname = modname.substr(0, modname.find(','));
            std::replace(modname.begin(), modname.end(), '-', '_');
            modinit_db[name][initcb] = modname; // init symbol should be unique within built-in.a
            modcb_db[modname].insert(initcb);
            if (alias != "x") {
                db << "prep" << " " << initcb << " " << modname << " " << alias << "\n";
                if (alias.substr(0, 3) == "of:")
                    db << "prep" << " " << initcb << " " << modname << " " << alias << "C*\n";
            }
        }
    }

    // Build register api list
    std::map<std::string, std::string> regapis;
    std::set<std::string> known_apis ({"driver_register"});
    uint32_t sz;
    std::set<std::string> allbclist;
    std::ifstream allbc(AllBCs);
    for (std::string line; std::getline(allbc, line);) {
        allbclist.insert(line);
    }
    llvm::SMDiagnostic ctxerr;
    llvm::LLVMContext context;
    do {
        sz = regapis.size();
        for (auto bc : allbclist) {
            std::unique_ptr<llvm::Module> module = llvm::parseIRFile(bc, ctxerr, context);
            if (!module)	continue;
            for (auto func = module->begin(); func != module->end(); func++) {
                for (auto bb = func->begin(); bb != func->end(); bb++) {
                    for (auto inst = bb->begin(); inst != bb->end(); inst++) {
                        llvm::Instruction *i = &(*inst);
                        if(llvm::isa<llvm::CallBase>(i)) {
                            llvm::CallBase *call = llvm::dyn_cast<llvm::CallBase>(i);
                            if (call->isInlineAsm() || call->isIndirectCall())    continue;
                            //  %call6 = call i32 null(ptr noundef %skb, ptr noundef %data.i)
                            if (!call->getCalledOperand())
                                continue;
                            if (llvm::isa<llvm::ConstantPointerNull>(call->getCalledOperand())) continue;
                            if (known_apis.find(call->getCalledOperand()->getName().str()) \
                                    != known_apis.end()) {
                                regapis[func->getName().str()] = module->getName().str();
                            }
                        }
                    }
                }
            }
        }
        for (auto api : regapis) {
            if (api.first == "init_module")	continue;
            known_apis.insert(api.first);
        }
    } while(sz < regapis.size());
    for (auto api : regapis) {
        llvm::outs() << "known_apis: " << api.first << " : " << api.second << "\n";
        pci_register_func.insert(api.first);
    }
    pci_register_func.insert("driver_register");

    // Extract device ids
    if (!InputFile.empty())
        processModuleFile(InputFile, db, err);
    else {
        for (auto tup : modinit_db)
            processModuleFile(tup.first, db, err);
    }

    if (!AliasFile.empty()) {
        std::ifstream aliasdb(AliasFile);
        for (std::string line; std::getline(aliasdb, line);) {
            std::string alias = line.substr(line.find(' ')+1, line.rfind(' ')-line.find(' ')-1);
            std::replace(alias.begin(), alias.end(), ' ', '_');
            std::string modname = line.substr(line.rfind(' ')+1);
            if (alias.find(':') == std::string::npos)
                continue;
            if (alias.substr(0, 8) == "devname:")
                continue;
            for (auto fn : modcb_db[modname])
                db << "alias " << fn << " "
                    << modname << " "
                    << alias << "\n";
        }
    }

    db.close();
    err.close();
    return 0;
}
