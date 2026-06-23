import HeroSection from "@/components/sections/HeroSection";
import StatsSection from "@/components/sections/StatsSection";
import ServicesSection from "@/components/sections/ServicesSection";
import AiSection from "@/components/sections/AiSection";
import SpecialtySection from "@/components/sections/SpecialtySection";
import CaseStudySection from "@/components/sections/CaseStudySection";
import PricingSection from "@/components/sections/PricingSection";
import ContactSection from "@/components/sections/ContactSection";
import ScrollFade from "@/components/ui/ScrollFade";

export default function Home() {
  return (
    <>
      <HeroSection />
      <ScrollFade><StatsSection /></ScrollFade>
      <ScrollFade><ServicesSection /></ScrollFade>
      <ScrollFade><AiSection /></ScrollFade>
      <ScrollFade><SpecialtySection /></ScrollFade>
      <ScrollFade><CaseStudySection /></ScrollFade>
      <ScrollFade><PricingSection /></ScrollFade>
      <ScrollFade><ContactSection /></ScrollFade>
    </>
  );
}
