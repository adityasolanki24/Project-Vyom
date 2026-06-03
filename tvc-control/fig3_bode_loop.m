%% fig3_bode_loop.m 
%  Bode plot of the compensated open-loop L(s) = C(s)G(s)

tvc_params;

figure('Color','w','Position',[100 100 560 420]);
margin(L);          %  draws the Bode plot AND annotates GM/PM
grid on;
set(findall(gcf,'Type','line'),'LineWidth',1.4);
set(gca,'FontSize',11);

exportgraphics(gcf,'fig_bode_loop.pdf','ContentType','vector');
disp('saved fig_bode_loop.pdf');
