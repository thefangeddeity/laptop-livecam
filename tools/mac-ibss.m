// Raise an ad-hoc (IBSS) network from macOS, or report honestly why not.
//
// The claim this exists to test: "macOS cannot do infrastructure-free wifi
// from a script." CoreWLAN's IBSS creation was deprecated in 10.10 and never
// removed -- the selector is still in the runtime on 14.x -- and IBSS is the
// ONE radio mode every node in this fleet has. Both Linux nodes' `iw phy`
// list it. It is the only common denominator there is.
//
// Why it matters for the house: BLE reaches one peer at about ten metres and
// carries messages only. An IBSS carries IP, so over it the viewer, the chat
// client and SSH all work between laptops with no router, no AP and no
// uplink. What it does NOT solve is a phone -- iOS will not join an IBSS.
//
// Reporting is the default, and raising it takes two words, because this
// machine LEAVES THE NETWORK to do it: the radio does one thing at a time,
// so the moment it beacons, the LAN, the tailnet and any ssh session over
// them are gone until the wifi is rejoined from the menu bar.
//
// Objective-C rather than Swift: the installed Swift toolchain and SDK
// disagree on a module version and refuse to build anything importing
// Foundation. clang does not care.

#import <Foundation/Foundation.h>
#import <CoreWLAN/CoreWLAN.h>
#import <objc/message.h>

static const char *MODE[] = {"none", "station", "IBSS", "hostAP"};

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        CWInterface *iface = [[CWWiFiClient sharedWiFiClient] interface];
        if (!iface) { printf("no wifi interface\n"); return 1; }

        BOOL wantStart = (argc > 1 && strcmp(argv[1], "--start") == 0);
        NSInteger mode = [iface interfaceMode];

        printf("interface   %s\n", [[iface interfaceName] UTF8String] ?: "?");
        printf("powered     %s\n", [iface powerOn] ? "yes" : "no");
        printf("mode        %ld (%s)\n", (long)mode,
               (mode >= 0 && mode <= 3) ? MODE[mode] : "?");
        printf("ssid        %s\n", [[iface ssid] UTF8String] ?: "-");
        CWChannel *ch = [iface wlanChannel];
        printf("channel     %s\n", ch ? [[NSString stringWithFormat:@"%ld",
               (long)[ch channelNumber]] UTF8String] : "-");

        // Ask the runtime, not the documentation.
        SEL sel = NSSelectorFromString(
            @"startIBSSModeWithSSID:security:channel:password:error:");
        BOOL present = [iface respondsToSelector:sel];
        printf("ibss call   %s\n", present ? "present in runtime"
                                           : "ABSENT -- this macOS removed it");
        if (!present) return 2;

        if (!wantStart) {
            printf("\nReporting only. To actually raise it:\n");
            printf("    mac-ibss --start <ssid> [channel] [wep-password]\n\n");
            printf("This machine LEAVES THE NETWORK when it does. Expect to\n");
            printf("lose the LAN, the tailnet and every ssh session over them\n");
            printf("until the wifi is rejoined from the menu bar.\n");
            return 0;
        }

        NSString *ssid = (argc > 2) ? @(argv[2]) : @"elemesh-adhoc";
        NSInteger channel = (argc > 3) ? atoi(argv[3]) : 11;
        NSString *password = (argc > 4) ? @(argv[4]) : nil;
        // 0 = open. WEP is the only thing IBSS ever offered and it is not
        // security; the mesh's own passphrase is what protects the messages.
        NSUInteger security = password ? 1 : 0;

        NSData *ssidData = [ssid dataUsingEncoding:NSUTF8StringEncoding];
        NSError *err = nil;

        printf("\nraising IBSS \"%s\" on channel %ld...\n",
               [ssid UTF8String], (long)channel);

        BOOL (*start)(id, SEL, NSData *, NSUInteger, NSInteger,
                      NSString *, NSError **) = (void *)objc_msgSend;
        BOOL ok = start(iface, sel, ssidData, security, channel, password, &err);

        if (ok) {
            printf("UP. mode now %ld, ssid %s\n",
                   (long)[iface interfaceMode], [[iface ssid] UTF8String] ?: "-");
            printf("Peers join by selecting \"%s\". Rejoin your own network\n",
                   [ssid UTF8String]);
            printf("from the menu bar to undo this.\n");
            return 0;
        }
        printf("REFUSED: %s\n", [[err localizedDescription] UTF8String]
                                ?: "no error given");
        printf("The selector exists and the driver declined. That is a\n");
        printf("measurement, not a permission problem -- record it and stop\n");
        printf("claiming either way.\n");
        return 3;
    }
}
