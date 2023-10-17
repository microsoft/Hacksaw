// SPDX-License-Identifier: MIT
// Copyright (c) 2023, Microsoft Corporation.
#include "llvm/Pass.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/ADT/SmallString.h"
#include <set>

using namespace llvm;

const char *export_prefix = "__UNIQUE_ID___addressable_";
const int prefix_len = 26;

namespace {
  std::set<StringRef> exports;
  std::set<Function*> expFuncs;
  std::set<StringRef> devFuncs;
  std::set<StringRef> drvFuncs;

  struct DrvdevregPass : public ModulePass {
    static char ID;
    DrvdevregPass() : ModulePass(ID) {}
    virtual bool runOnModule(Module &M) {
      Module *m = &M;
      for (Module::global_iterator i = m->global_begin(), e = m->global_end(); i != e; ++i) {
        GlobalVariable &GV = *i;
        StringRef gvName = GV.getName();
        if (gvName.startswith(export_prefix)) {
          // TODO: find better way to identify the suffix length
          int suffix_len = 0;
          while (true) {
            char val = gvName[gvName.size()-1-suffix_len];
            if (val < '0' || val > '9')
              break;
            else
              suffix_len++;
          }
          exports.insert(gvName.drop_front(prefix_len).drop_back(suffix_len));
        }
      }

      devFuncs.insert("device_add");
      devFuncs.insert("device_del");
      devFuncs.insert("device_register");
      devFuncs.insert("device_unregister");
      // devFuncs.insert("misc_register");
      // devFuncs.insert("misc_unregister");

      drvFuncs.insert("driver_register");
      drvFuncs.insert("driver_unregister");

      auto noDevFuncs = devFuncs.size();
      while (true) {
        for (auto &F : M) {
          bool done = false;
          for (auto &BB : F) {
            for (auto &Inst : BB) {
              if (auto ci = dyn_cast<CallBase>(&Inst)) {
                Value *fn = ci->getCalledOperand();
                if (fn) {
                  auto s = devFuncs.find(fn->getName());
                  if (s != devFuncs.end()) {
                    devFuncs.insert(F.getName());
                    done = true;
                    break;
                  }
                }
              }
            }
            if (done)
              break;
          }
        }

        if (noDevFuncs == devFuncs.size())
          break;
        else
          noDevFuncs = devFuncs.size();
      }

      auto noDrvFuncs = drvFuncs.size();
      while (true) {
        for (auto &F : M) {
          bool done = false;
          for (auto &BB : F) {
            for (auto &Inst : BB) {
              if (auto ci = dyn_cast<CallBase>(&Inst)) {
                Value *fn = ci->getCalledOperand();
                if (fn) {
                  auto s = drvFuncs.find(fn->getName());
                  if (s != drvFuncs.end()) {
                    drvFuncs.insert(F.getName());
                    done = true;
                    break;
                  }
                }
              }
            }
            if (done)
              break;
          }
        }

        if (noDrvFuncs == drvFuncs.size())
          break;
        else
          noDrvFuncs = drvFuncs.size();
      }

      for (auto &F : M) {
        if (F.arg_empty() || F.getName() == "init_module" || F.getName() == "cleanup_module")
          continue;

        auto s = exports.find(F.getName());
        if (s != exports.end())
          expFuncs.insert(&F);
      }

      for (auto F : expFuncs) {
        for (auto &BB : *F) {
          for (auto &Inst : BB) {
            if (auto ci = dyn_cast<CallBase>(&Inst)) {
              Value *fn = ci->getCalledOperand();
              if (fn) {
                auto s = devFuncs.find(fn->getName());
                if (s != devFuncs.end()) {
                  Module *m = Inst.getModule();
                  if (m)
                    errs() << "class: " << m->getName() << " " << F->getName() << "\n";
                }

                auto s2 = drvFuncs.find(fn->getName());
                if (s2 != drvFuncs.end()) {
                  Module *m = Inst.getModule();
                  if (m)
                    errs() << "bus_type: " << m->getName() << " " << F->getName() << "\n";
                }
              }
            }
          }
        }
      }

      return false;
    }
  };
}

char DrvdevregPass::ID = 0;
static RegisterPass<DrvdevregPass> X("drvdevreg", "Driver/Device Registration Pass", false, false);
